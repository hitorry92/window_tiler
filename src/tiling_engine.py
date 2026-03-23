# -*- coding: utf-8 -*-
import threading
import win32gui
import time
import ctypes
from .win_utils import (
    get_monitor_info,
    move_window_precision,
    is_valid_window,
    is_window_in_rect,
)


class WindowTracker:
    def __init__(
        self, monitor_index, profiles, monitor_config, ui_update_callback=None
    ):
        self.monitor_index = monitor_index
        self.profiles = profiles
        self.monitor_config = (
            monitor_config  # {"profile": "...", "main_slot_index": ...}
        )
        self.ui_update_callback = ui_update_callback

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.slots = []
        self.slot_rects = []
        self.monitor_info = None
        self.is_paused = True  # 시작 시 정지 상태로 시작 (사용자 요청)
        self.is_assignment_mode = False
        self.assignment_queue = []  # 순서대로 채울 슬롯 인덱스 리스트

        self.overlay_manager = None

        self.check_thread = None

        self.update_layout()

    def start(self):
        self.stop_event.clear()
        self.check_thread = threading.Thread(target=self._periodic_check, daemon=True)
        self.check_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.check_thread:
            self.check_thread.join()

    def _periodic_check(self):
        """백그라운드에서 주기적으로 창 유효성을 검사하는 스레드"""
        while not self.stop_event.wait(2):  # 2초마다 체크
            needs_ui_update = False
            with self.lock:
                for i, slot in enumerate(list(self.slots)):  # 복사본 순회
                    if slot["hwnd"] and not win32gui.IsWindow(slot["hwnd"]):
                        # 고정된 슬롯은 창만 비우고, 고정되지 않은 슬롯은 전체를 초기화
                        if not slot.get("locked"):
                            self.slots[i] = {
                                "hwnd": None,
                                "locked": False,
                                "overlay_enabled": slot.get("overlay_enabled", True),
                            }
                        else:
                            self.slots[i]["hwnd"] = None
                        needs_ui_update = True

            if needs_ui_update and self.ui_update_callback:
                self.ui_update_callback()

    def set_overlay_manager(self, manager):
        self.overlay_manager = manager

    def _remove_overlay(self, index):
        if self.overlay_manager and index in self.overlay_manager.overlays:
            try:
                self.overlay_manager.overlays[index].destroy()
                del self.overlay_manager.overlays[index]
            except:
                pass

    def refresh_overlays(self):
        if not self.overlay_manager:
            return
        # 일시 정지 상태이거나 대화형 할당 모드일 때는 오버레이 숨김
        if self.is_paused or self.is_assignment_mode:
            self.overlay_manager.update_overlays([])
            return

        main_idx = self.monitor_config.get("main_slot_index", 0)
        active_slots = []
        for i, slot in enumerate(self.slots):
            if (
                i != main_idx
                and slot.get("hwnd")
                and win32gui.IsWindow(slot["hwnd"])
                and slot.get("overlay_enabled", True)
            ):
                active_slots.append((i, self.slot_rects[i]["rect"], slot["hwnd"]))
        self.overlay_manager.update_overlays(active_slots)

    def swap_slots(self, index1, index2):
        with self.lock:
            slot1 = self.slots[index1]
            slot2 = self.slots[index2]

            # 고정된 슬롯은 덮개와 관계없이 스왑 불가
            if slot1.get("locked") or slot2.get("locked"):
                return False

            # 덮개가 꺼진 슬롯도 스왑 불가 (고정과 동일하게 보호)
            if not slot1.get("overlay_enabled", True) or not slot2.get(
                "overlay_enabled", True
            ):
                return False

            self.slots[index1], self.slots[index2] = slot2, slot1
            self.reposition_all()
            if self.ui_update_callback:
                self.ui_update_callback()
            return True

    def toggle_slot_lock(self, index):
        with self.lock:
            self.slots[index]["locked"] = not self.slots[index].get("locked", False)
            if self.ui_update_callback:
                self.ui_update_callback()

    def toggle_overlay(self, index):
        with self.lock:
            current = self.slots[index].get("overlay_enabled", True)
            self.slots[index]["overlay_enabled"] = not current

            # 덮개를 끄면 즉시 오버레이 제거
            if (
                not self.slots[index].get(
                    "overlay_enabled", True
                )  # 새 값이 꺼짐인지 확인
                and self.overlay_manager
                and index in self.overlay_manager.overlays
            ):
                try:
                    self.overlay_manager.overlays[index].destroy()
                    del self.overlay_manager.overlays[index]
                except:
                    pass

            self.refresh_overlays()
            if self.ui_update_callback:
                self.ui_update_callback()

    def swap_to_main(self, target_idx):
        with self.lock:
            if target_idx < 0 or target_idx >= len(self.slots):
                return
            main_idx = self.monitor_config.get("main_slot_index", 0)
            if main_idx >= len(self.slots):
                main_idx = 0

            # 고정된 슬롯과는 스왑하지 않음 (덮개와 상관없이)
            main_locked = self.slots[main_idx].get("locked", False)
            target_locked = self.slots[target_idx].get("locked", False)
            if main_locked or target_locked:
                return

            if main_idx == target_idx:
                return

            self.slots[main_idx], self.slots[target_idx] = (
                self.slots[target_idx],
                self.slots[main_idx],
            )
            self.reposition_all()
            if self.ui_update_callback:
                self.ui_update_callback()

    def update_layout(self):
        with self.lock:
            self.monitor_info = get_monitor_info(self.monitor_index)
            if not self.monitor_info:
                return

            profile_name = self.monitor_config.get("profile", "기본")
            # 1순위: 지정 프로필, 2순위: '기본' 프로필, 3순위: 첫 번째 프로필, 4순위: 빈 프로필 (Cycle 15 강화)
            profile = self.profiles.get(profile_name) or self.profiles.get("기본")
            if not profile and self.profiles:
                profile = next(iter(self.profiles.values()))
            if not profile:
                profile = {"horizontal": [], "vertical": [], "main_slot_index": 0}

            h_splits = profile.get("horizontal", [])
            v_splits = profile.get("vertical", [])
            merges = profile.get("merges", [])

            m = self.monitor_info
            gap = self.monitor_config.get("gap", 0)
            self.slot_rects = self._calculate_slots(
                m["x"], m["y"], m["width"], m["height"], h_splits, v_splits, merges, gap
            )

            # 슬롯 데이터 구조 상태 동기화
            num_slots = len(self.slot_rects)
            while len(self.slots) < num_slots:
                self.slots.append(
                    {"hwnd": None, "locked": False, "overlay_enabled": True}
                )
            self.slots = self.slots[:num_slots]

    def _calculate_slots(self, x, y, w, h, h_splits, v_splits, merges=None, gap=0):
        h_points = [0.0] + sorted(h_splits) + [1.0]
        v_points = [0.0] + sorted(v_splits) + [1.0]

        base_slots = []
        for i in range(len(h_points) - 1):
            for j in range(len(v_points) - 1):
                sx = int(x + v_points[j] * w)
                sy = int(y + h_points[i] * h)
                sw = int(v_points[j + 1] * w - v_points[j] * w)
                sh = int(h_points[i + 1] * h - h_points[i] * h)

                # Gap 마진 적용 (Cycle 15)
                # (sx+gap, sy+gap, sw-2*gap, sh-2*gap)
                rect = (sx + gap, sy + gap, max(1, sw - 2 * gap), max(1, sh - 2 * gap))
                base_slots.append({"rect": rect, "base_indices": [len(base_slots)]})

        if not merges:
            return base_slots

        # 슬롯 병합 처리
        merged_map = {}  # 원래 인덱스 -> 그룹 ID
        for i, group in enumerate(merges):
            for idx in group:
                merged_map[idx] = i

        final_slots = []
        groups_added = set()

        for idx in range(len(base_slots)):
            if idx in merged_map:
                gid = merged_map[idx]
                if gid not in groups_added:
                    # 그룹 전체를 아우르는 사각형 계산
                    group = merges[gid]
                    gx = min(
                        base_slots[i]["rect"][0] for i in group if i < len(base_slots)
                    )
                    gy = min(
                        base_slots[i]["rect"][1] for i in group if i < len(base_slots)
                    )
                    g_right = max(
                        base_slots[i]["rect"][0] + base_slots[i]["rect"][2] + gap
                        for i in group
                        if i < len(base_slots)
                    )
                    g_bottom = max(
                        base_slots[i]["rect"][1] + base_slots[i]["rect"][3] + gap
                        for i in group
                        if i < len(base_slots)
                    )
                    # 병합된 슬롯은 내부 gap을 무시하고 전체 영역에 다시 gap 적용
                    final_slots.append(
                        {
                            "rect": (gx, gy, g_right - gx, g_bottom - gy),
                            "base_indices": list(group),
                        }
                    )
                    groups_added.add(gid)
            else:
                final_slots.append(base_slots[idx])

        return final_slots

    def on_focus_event(self, hwnd):
        if self.is_paused and not self.is_assignment_mode:
            return
        if not is_valid_window(hwnd):
            return

        # [NEW] 마우스 왼쪽 버튼(0x01)이 떨어질 때까지 최대 0.5초 대기
        # MSB(최상위 비트)가 1이면 눌린 상태 (0x8000)
        timeout = 50
        while (ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000) and timeout > 0:
            time.sleep(0.01)
            timeout -= 1

        # 1. 대화형 할당 모드 처리 (Cycle 15)
        if self.is_assignment_mode:
            title = win32gui.GetWindowText(hwnd)
            if self.handle_assignment(hwnd, title):
                return

        if self.is_paused:
            return

        with self.lock:
            # 배정 기록에 없는 창은 무시
            if not any(s["hwnd"] == hwnd for s in self.slots):
                return

            # 해당 창이 현재 모니터 영역 안에 있는지 확인
            m = self.monitor_info
            if not is_window_in_rect(hwnd, (m["x"], m["y"], m["width"], m["height"])):
                return

            # 메인 슬롯 인덱스 확인
            main_idx = self.monitor_config.get("main_slot_index", 0)
            if main_idx >= len(self.slot_rects):
                main_idx = 0

            # 이미 메인 슬롯에 있는 창이면 무시
            if self.slots[main_idx]["hwnd"] == hwnd:
                return

            # 다른 슬롯에 있던 창인지 확인
            old_idx = -1
            for i, s in enumerate(self.slots):
                if s["hwnd"] == hwnd:
                    old_idx = i
                    break

            # 기존 메인 창
            old_main = self.slots[main_idx]["hwnd"]

            # 메인 슬롯이 고정되어 있으면 스왑 불가
            if self.slots[main_idx].get("locked"):
                return

            # 기존 창이 있는 슬롯이 고정되어 있으면 스왑 불가
            if old_idx != -1 and self.slots[old_idx].get("locked"):
                return

            # 스왑
            self.slots[main_idx]["hwnd"] = hwnd
            if old_idx != -1:
                self.slots[old_idx]["hwnd"] = old_main

            self.reposition_all()

    def reposition_all(self):
        # 자동 타일링이 pause 상태여도, 명시적 호출 시에는 배치를 수행함
        for i, slot in enumerate(self.slots):
            hwnd = slot["hwnd"]
            if hwnd and win32gui.IsWindow(hwnd):
                rect = self.slot_rects[i]["rect"]
                move_window_precision(hwnd, *rect)
        self.refresh_overlays()

    def force_refresh(self):
        self.update_layout()
        self.reposition_all()

    def auto_fill_all_slots(self):
        """현재 열려 있는 상위 창들을 각 슬롯에 자동 배분 (Cycle 15)"""
        from .win_utils import get_window_list

        # 현재 모니터의 활성 창 목록 가져오기
        windows = get_window_list(self.monitor_info)
        # 자신(Window Tiler) 제외
        my_hwnd = win32gui.GetForegroundWindow()  # 좀 더 확실한 자기 자신 찾기
        targets = [w for w in windows if w[0] != my_hwnd and "Window Tiler" not in w[1]]

        with self.lock:
            num_slots = len(self.slot_rects)
            main_idx = self.monitor_config.get("main_slot_index", 0)
            if main_idx >= num_slots:
                main_idx = 0

            # 1. 메인 슬롯 우선 배치를 위한 순서 생성
            fill_order = [main_idx] + [i for i in range(num_slots) if i != main_idx]

            # 2. 순서에 따라 창 배정 (고정된 슬롯은 보호)
            if not self.slots:
                self.slots = [
                    {"hwnd": None, "locked": False, "overlay_enabled": True}
                    for _ in range(num_slots)
                ]
            else:
                for s in self.slots:
                    if not s.get("locked", False):
                        s["hwnd"] = None

            for i, slot_idx in enumerate(fill_order):
                if not self.slots[slot_idx].get("locked", False) and i < len(targets):
                    self.slots[slot_idx]["hwnd"] = targets[i][0]

            self.reposition_all()
            return sum(1 for s in self.slots if s["hwnd"])

    def start_assignment_mode(self):
        """사용자가 클릭하는 순서대로 슬롯에 할당하는 모드 시작 (메인 우선)"""
        num_slots = len(self.slot_rects)
        main_idx = self.monitor_config.get("main_slot_index", 0)
        if main_idx >= num_slots:
            main_idx = 0

        # 순서: 메인 슬롯 -> 나머지 0번부터 순차
        queue = [main_idx]
        for i in range(num_slots):
            if i != main_idx:
                queue.append(i)

        with self.lock:
            self.assignment_queue = queue
            self.is_assignment_mode = True
        return num_slots

    def handle_assignment(self, hwnd, title):
        """포커스된 창을 대기열의 다음 슬롯에 할당"""
        with self.lock:
            if not self.is_assignment_mode or not self.assignment_queue:
                self.is_assignment_mode = False
                return False

            slot_idx = self.assignment_queue.pop(0)

            # 기존 슬롯들에 해당 HWND가 있다면 제거 (중복 방지)
            for i in range(len(self.slots)):
                if self.slots[i]["hwnd"] == hwnd:
                    self.slots[i]["hwnd"] = None

            self.slots[slot_idx]["hwnd"] = hwnd
            self.reposition_all()

            if not self.assignment_queue:
                self.is_assignment_mode = False
            return True
