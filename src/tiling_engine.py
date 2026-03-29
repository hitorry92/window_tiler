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
    get_monitor_dpi_scale_by_hwnd,
    get_monitor_dpi_scale,
)
from .app_config import DEFAULT_SWAP_MODE, DEFAULT_PROFILE, get_config_value


# [이해 포인트] 이 클래스는 전체 프로그램의 심장이자 뇌 역할을 합니다.
# 창을 가둘 '슬롯(영역)'을 계산하고, 열려있는 창(HWND)을 슬롯에 매핑하며, 포커스 변경 시 자리를 바꾸는(Swap) 모든 로직을 관장합니다.
class WindowTracker:
    def __init__(
        self,
        monitor_index,
        profiles,
        monitor_config,
        ui_update_callback=None,
        app_config=None,
        request_global_swap_callback=None,
    ):
        self.monitor_index = monitor_index
        self.profiles = profiles  # 전체 프로필 데이터 (분할 비율 등)
        self.monitor_config = monitor_config  # 현재 모니터에 적용된 설정 (프로필 이름, 메인 슬롯 인덱스 등)
        self.config = app_config  # 전체 앱 설정 (글로벌 모드 확인용)
        self.ui_update_callback = (
            ui_update_callback  # 상태 변경 시 UI를 새로고침하기 위한 콜백 함수
        )
        self.request_global_swap_callback = request_global_swap_callback

        # [위험] 이 엔진은 백그라운드 검사 스레드, 핫키 스레드, 윈도우 훅 스레드에서 동시다발적으로 접근됩니다.
        # 따라서 self.slot_manager.slots나 self.slot_rects 같은 중요 데이터를 읽거나 쓸 때는 반드시 self.lock을 걸어야 Race Condition을 막을 수 있습니다.
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        # [핵심 변수] self.slot_manager.slots와 self.slot_rects는 1:1로 매칭되는 인덱스를 갖습니다.
        # self.slot_rects: 각 슬롯의 좌표 (x, y, w, h)를 가짐.
        from .core.slot_manager import SlotManager

        self.slot_manager = SlotManager(0)
        self.slot_rects = []

        self.monitor_info = None
        self.is_paused = True  # 시작 시 일시 정지 상태로 시작 (사용자 요청)
        self.is_assignment_mode = False
        self.assignment_queue = []  # 대화형 할당 시 순서대로 채울 슬롯 인덱스 리스트

        self.overlay_manager = None
        self.check_thread = None

        # 생성 즉시 프로필과 모니터 해상도를 기반으로 슬롯의 물리적 위치(rect)를 계산합니다.
        self.update_layout()

    @property
    def slots(self):
        return self.slot_manager.slots

    @slots.setter
    def slots(self, value):
        self.slot_manager.slots = value

    def start(self):
        """백그라운드 유효성 검사 스레드를 시작합니다."""
        self.stop_event.clear()
        self.check_thread = threading.Thread(target=self._periodic_check, daemon=True)
        self.check_thread.start()

    def stop(self):
        """엔진을 정지하고 스레드를 정리합니다."""
        self.stop_event.set()
        if self.check_thread:
            self.check_thread.join()

    def _periodic_check(self):
        """
        [로직] 백그라운드에서 2초마다 창이 닫히거나 사라졌는지 검사합니다.
        사용자가 'X' 버튼으로 창을 꺼버린 경우, 엔진은 이를 알아채고 해당 슬롯을 비워야 합니다.
        """
        while not self.stop_event.wait(2):  # 2초 대기 후 실행
            needs_ui_update = False
            with self.lock:
                needs_ui_update = self.slot_manager.clear_invalid_hwnds()

            # 변경사항이 발생했다면 UI를 새로고침합니다.
            if needs_ui_update and self.ui_update_callback:
                self.ui_update_callback()

    def set_overlay_manager(self, manager):
        """투명 덮개를 관리하는 객체를 연결합니다."""
        self.overlay_manager = manager

    def _remove_overlay(self, index):
        """특정 슬롯의 투명 덮개를 제거합니다."""
        if self.overlay_manager and index in self.overlay_manager.overlays:
            try:
                self.overlay_manager.overlays[index].destroy()
                del self.overlay_manager.overlays[index]
            except:
                pass

    def refresh_overlays(self):
        """
        [로직] 각 슬롯의 상태에 따라 투명 덮개(Overlay)를 업데이트합니다.
        덮개는 사이드 슬롯의 클릭 오작동을 막아주는 얇은 방어막 역할을 합니다.
        """
        if not self.overlay_manager:
            return

        # 일시 정지 상태이거나 대화형 할당 모드일 때는 화면을 가리면 안 되므로 덮개를 모두 숨깁니다.
        if self.is_paused or self.is_assignment_mode:
            self.overlay_manager.update_overlays([])
            return

        main_idx = self.monitor_config.get("main_slot_index", 0)

        # [수정] 글로벌 스왑 모드일 경우, 로컬 메인 슬롯(main_idx)은 일반 슬롯 취급하고 오직 글로벌 메인 슬롯만 덮개를 뺍니다.
        swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)
        g_mon = get_config_value(self.config, "global_main_monitor", 0)
        g_slot = get_config_value(self.config, "global_main_slot", 0)
        is_global_main_mon = swap_mode == "global" and self.monitor_index == g_mon

        active_slots = []
        for i, slot in enumerate(self.slot_manager.slots):
            # 덮개를 씌워야 하는 조건 판단
            needs_overlay = False
            if swap_mode == "global":
                # 글로벌 모드: 오직 자기가 지정된 글로벌 메인일 때만 덮개를 뺌
                if not (is_global_main_mon and i == g_slot):
                    needs_overlay = True
            else:
                # 로컬 모드: 자기가 로컬 메인이면 덮개를 뺌
                if i != main_idx:
                    needs_overlay = True

            if (
                needs_overlay
                and slot.get("hwnd")
                and win32gui.IsWindow(slot["hwnd"])
                and slot.get("overlay_enabled", True)
            ):
                active_slots.append((i, self.slot_rects[i]["rect"], slot["hwnd"]))

        # Overlay Manager에게 계산된 활성 덮개 리스트를 넘겨 GUI를 업데이트하게 합니다.
        self.overlay_manager.update_overlays(active_slots)

    def swap_slots(self, index1, index2):
        """[로직] 두 슬롯의 창을 강제로 위치 변경(스왑)합니다. (드래그 앤 드롭 등에서 사용)"""
        with self.lock:
            success = self.slot_manager.swap(index1, index2)

            if success:
                self.reposition_all()  # 윈도우 물리적 위치 이동
                if self.ui_update_callback:
                    self.ui_update_callback()
            return success

    def toggle_slot_lock(self, index):
        """특정 슬롯의 고정 상태를 토글합니다."""
        with self.lock:
            self.slot_manager.toggle_lock(index)
            if self.ui_update_callback:
                self.ui_update_callback()

    def toggle_overlay(self, index):
        """특정 슬롯의 덮개(방어막) 상태를 토글합니다."""
        with self.lock:
            changed = self.slot_manager.toggle_overlay(index)

            # 덮개를 껐다면 즉시 제거해줍니다.
            if (
                not self.slot_manager.slots[index]["overlay_enabled"]
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
        """[로직] 단축키나 클릭 이벤트를 받았을 때 특정 슬롯을 메인 슬롯과 자리를 바꿉니다."""
        with self.lock:
            if target_idx < 0 or target_idx >= len(self.slot_manager.slots):
                return
            main_idx = self.monitor_config.get("main_slot_index", 0)
            if main_idx >= len(self.slot_manager.slots):
                main_idx = 0

            # 메인이나 타겟이 고정되어 있다면 무시합니다.
            if self.slot_manager.slots[main_idx].get(
                "locked", False
            ) or self.slot_manager.slots[target_idx].get("locked", False):
                return

            if main_idx == target_idx:
                return

            # 스왑
            self.slot_manager.slots[main_idx], self.slot_manager.slots[target_idx] = (
                self.slot_manager.slots[target_idx],
                self.slot_manager.slots[main_idx],
            )
            self.reposition_all()

            if self.ui_update_callback:
                self.ui_update_callback()

    def update_layout(self):
        """
        [핵심 로직] 프로필 데이터를 바탕으로 모니터 해상도에 맞게 슬롯의 물리적 위치(x, y, w, h)를 쪼개서 계산합니다.
        """
        with self.lock:
            self.monitor_info = get_monitor_info(self.monitor_index)
            if not self.monitor_info:
                return

            # 프로필 가져오기 우선순위 로직
            profile_name = self.monitor_config.get("profile", DEFAULT_PROFILE)
            profile = self.profiles.get(profile_name) or self.profiles.get(
                DEFAULT_PROFILE
            )
            if not profile and self.profiles:
                profile = next(iter(self.profiles.values()))
            if not profile:
                profile = {"horizontal": [], "vertical": [], "main_slot_index": 0}

            h_splits = profile.get("horizontal", [])
            v_splits = profile.get("vertical", [])
            merges = profile.get("merges", [])
            gap = self.monitor_config.get("gap", 0)

            # [이해 포인트] _calculate_slots에서 실제 좌표 배열(slot_rects)을 만들어 옵니다.
            self.slot_rects = self._calculate_slots(
                self.monitor_info["x"],
                self.monitor_info["y"],
                self.monitor_info["width"],
                self.monitor_info["height"],
                h_splits,
                v_splits,
                merges,
                gap,
            )

            # 슬롯 갯수가 변경되었을 수 있으므로 self.slot_manager.slots(창 상태 배열)의 크기를 맞춥니다.
            num_slots = len(self.slot_rects)
            while len(self.slot_manager.slots) < num_slots:
                self.slot_manager.slots.append(
                    {"hwnd": None, "locked": False, "overlay_enabled": True}
                )
            self.slot_manager.slots = self.slot_manager.slots[:num_slots]

    def _calculate_slots(self, x, y, w, h, h_splits, v_splits, merges=None, gap=0):
        from .core.layout_calculator import LayoutCalculator

        return LayoutCalculator.calculate_slots(
            x, y, w, h, h_splits, v_splits, merges, gap
        )

    def on_focus_event(self, hwnd):
        """
        [이해 포인트] 사용자가 마우스나 Alt+Tab으로 새로운 창에 포커스를 주었을 때 OS 이벤트 훅에 의해 불립니다.
        엔진의 가장 동적인(다이나믹한) 부분입니다.
        """
        if self.is_paused and not self.is_assignment_mode:
            return
        if not is_valid_window(hwnd):  # 시스템 숨김창, 태스크바 등 무시
            return

        # [안전 장치] 사용자가 창 제목표시줄을 '드래그' 중일 때는 스왑되면 안 되므로 마우스 왼쪽 버튼(0x01)이 떨어질 때까지 기다림
        timeout = 50
        while (ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000) and timeout > 0:
            time.sleep(0.01)
            timeout -= 1

        # 1. 사용자가 "선택 지정 모드"를 눌러 순서대로 클릭 중인 경우
        if self.is_assignment_mode:
            title = win32gui.GetWindowText(hwnd)
            if self.handle_assignment(hwnd, title):
                return

        if self.is_paused:
            return

        # [1단계: 결정] Lock 안에서는 어떤 행동을 할지 '결정'만 하고 변수에 저장합니다.
        action = None
        swap_request_args = None

        with self.lock:
            if not any(s["hwnd"] == hwnd for s in self.slot_manager.slots):
                return
            m = self.monitor_info
            if not is_window_in_rect(hwnd, (m["x"], m["y"], m["width"], m["height"])):
                return

            old_idx = -1
            for i, s in enumerate(self.slot_manager.slots):
                if s["hwnd"] == hwnd:
                    old_idx = i
                    break

            if old_idx == -1:
                return

            swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)

            if swap_mode == "global":
                g_mon = get_config_value(self.config, "global_main_monitor", 0)
                if self.monitor_index != g_mon:
                    if self.request_global_swap_callback:
                        action = "request_global_swap"
                        swap_request_args = (self.monitor_index, old_idx)
                else:  # 자신이 글로벌 메인 모니터
                    main_idx = get_config_value(self.config, "global_main_slot", 0)
                    if self.slot_manager.slots[main_idx]["hwnd"] != hwnd:
                        action = "local_swap"
            else:  # 로컬 모드
                main_idx = self.monitor_config.get("main_slot_index", 0)
                if main_idx >= len(self.slot_manager.slots):
                    main_idx = 0
                if self.slot_manager.slots[main_idx]["hwnd"] != hwnd:
                    action = "local_swap"

        # [2단계: 실행] Lock 밖에서 결정된 행동을 실행합니다.
        if action == "request_global_swap":
            self.request_global_swap_callback(
                swap_request_args[0], swap_request_args[1]
            )
        elif action == "local_swap":
            # 로컬 스왑은 self.lock을 다시 사용하므로 별도 함수로 호출
            self.swap_to_main(old_idx)

    def reposition_all(self):
        """[핵심 행동] 현재 self.slot_manager.slots에 매핑된 상태 그대로 OS API를 이용해 실제 윈도우들을 이동시킵니다."""
        for i, slot in enumerate(self.slot_manager.slots):
            hwnd = slot["hwnd"]
            if hwnd and win32gui.IsWindow(hwnd):
                rect = self.slot_rects[i]["rect"]
                x, y, w, h = rect

                # win_utils.py에 있는 DWM 보정이 적용된 정밀 이동 함수 (Two-Step 렌더링 방식 호출)
                move_window_precision(hwnd, x, y, w, h)
        self.refresh_overlays()

    def force_refresh(self):
        """수동으로 레이아웃과 윈도우 배치를 강제 갱신합니다."""
        self.update_layout()
        self.reposition_all()

    def auto_fill_all_slots(self, excluded_windows=None):
        """
        [로직] 현재 화면에 켜져 있는 유효한 창들을 긁어모아 빈 슬롯에 전부 꽂아 넣습니다.
        """
        from .win_utils import get_window_list, is_own_window

        if excluded_windows is None:
            excluded_windows = []

        # 현재 모니터의 활성 창 목록 가져오기
        windows = get_window_list(self.monitor_info)

        # 자신(Window Tiler 설정창) 및 사용자가 지정한 예외 창 목록은 필터링
        my_hwnd = win32gui.GetForegroundWindow()
        targets = [
            w
            for w in windows
            if w[0] != my_hwnd
            and not is_own_window(w[1])
            and w[1] not in excluded_windows
        ]

        with self.lock:
            num_slots = len(self.slot_rects)
            swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)

            if swap_mode == "global":
                g_mon = get_config_value(self.config, "global_main_monitor", 0)
                g_slot = get_config_value(self.config, "global_main_slot", 0)

                # 자기가 글로벌 메인 모니터라면 글로벌 메인 슬롯부터 먼저 채웁니다.
                if self.monitor_index == g_mon:
                    main_idx = g_slot
                else:
                    # 메인 모니터가 아니면 그냥 순서대로 채웁니다.
                    main_idx = 0
            else:
                main_idx = self.monitor_config.get("main_slot_index", 0)

            if main_idx >= num_slots:
                main_idx = 0

            # 메인 슬롯부터 우선적으로 채우기 위한 순서 생성 (예: 메인이 2번이면 [2, 0, 1, 3])
            fill_order = [main_idx] + [i for i in range(num_slots) if i != main_idx]

            # 기존에 배정된 슬롯 초기화 (단, 잠긴 슬롯은 보호)
            if not self.slot_manager.slots:
                self.slot_manager.resize(num_slots)
            else:
                self.slot_manager.clear_unlocked_slots()

            # 현재 모든 슬롯에 배정된 창 HWND 수집 (고정 여부와 관계없이)
            already_assigned = self.slot_manager.get_assigned_hwnds()

            # 이미 배정된 창은 targets에서 제외 (중복 배정 방지)
            filtered_targets = [w for w in targets if w[0] not in already_assigned]

            # 필터링된 창들을 순서대로 밀어넣기
            for i, slot_idx in enumerate(fill_order):
                if not self.slot_manager.slots[slot_idx].get(
                    "locked", False
                ) and i < len(filtered_targets):
                    self.slot_manager.slots[slot_idx]["hwnd"] = filtered_targets[i][0]

            self.reposition_all()
            return sum(1 for s in self.slot_manager.slots if s["hwnd"])

    def start_assignment_mode(self):
        """
        사용자가 1번 클릭하면 메인, 2번 클릭하면 1번 슬롯... 처럼 순서대로 할당하는 모드를 시작합니다.
        (현재는 거의 사용되지 않고 WindowSelector GUI를 선호함)
        """
        num_slots = len(self.slot_rects)
        main_idx = self.monitor_config.get("main_slot_index", 0)
        if main_idx >= num_slots:
            main_idx = 0

        queue = [main_idx] + [i for i in range(num_slots) if i != main_idx]

        with self.lock:
            self.assignment_queue = queue
            self.is_assignment_mode = True
        return num_slots

    def handle_assignment(self, hwnd, title):
        """할당 모드 중일 때 포커스를 받은 창을 큐에 남은 다음 슬롯에 할당합니다."""
        with self.lock:
            if not self.is_assignment_mode or not self.assignment_queue:
                self.is_assignment_mode = False
                return False

            slot_idx = self.assignment_queue.pop(0)

            # 이미 다른 슬롯에 이 창이 있다면 비워줌 (중복 방지)
            for i in range(len(self.slot_manager.slots)):
                if self.slot_manager.slots[i]["hwnd"] == hwnd:
                    self.slot_manager.slots[i]["hwnd"] = None

            self.slot_manager.slots[slot_idx]["hwnd"] = hwnd
            self.reposition_all()

            if not self.assignment_queue:
                self.is_assignment_mode = False
            return True
