# -*- coding: utf-8 -*-
import sys
import threading
import ctypes
import traceback
import atexit  # [안전 장치] 프로그램 비정상 종료 시에도 리소스 해제를 보장하기 위해 추가
from threading import Event
from .app_config import load_config, load_profiles, save_config
from .win_utils import get_all_monitors
from .tiling_engine import WindowTracker
from .event_monitor import FocusMonitor
from .hotkey_manager import HotkeyManager
from .tray_manager import TrayManager
from .settings_gui import SettingsGUI
from .overlay_manager import OverlayManager

# [핵심 로직] 고해상도 모니터 대응을 위한 DPI 인식 설정
try:
    # Per-Monitor V2 설정 (-4)
    ctypes.windll.shcore.SetProcessDpiAwarenessContext(-4)
except (AttributeError, TypeError):
    # [안전 장치] 구형 윈도우(Windows 8.1 등)와의 호환성 처리
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class WindowTilerApp:
    def __init__(self):
        # [이해 포인트] 설정 및 프로필 로드
        self.config = load_config()
        self.profiles = load_profiles()
        self.gui = None

        self.trackers = {}  # 모니터 인덱스별 트래커 저장소
        monitors = get_all_monitors()

        # [핵심 로직] 각 모니터마다 독립적인 WindowTracker 인스턴스 생성
        for i, mon in enumerate(monitors):
            # 모니터별 설정 추출 및 보정
            mon_idx_str = str(i)
            if mon_idx_str not in self.config["monitor_configs"]:
                self.config["monitor_configs"][mon_idx_str] = {
                    "profile": "기본",
                    "main_slot_index": 0,
                }

            mon_config = self.config["monitor_configs"][mon_idx_str]
            # [이해 포인트] 각 트래커는 자신만의 설정, 상태를 독립적으로 관리함
            tracker = WindowTracker(
                i,
                self.profiles,
                mon_config,
                ui_update_callback=self._request_ui_update,
                app_config=self.config,
                request_global_swap_callback=self.handle_global_focus_swap,
            )
            self.trackers[i] = tracker

        # 현재 GUI에서 보고 있는 활성 모니터 인덱스
        self.active_monitor_index = self.config.get("monitor_index", 0)
        if self.active_monitor_index >= len(monitors):
            self.active_monitor_index = 0

        self.paused_event = threading.Event()
        self.paused_event.set()  # 초기 상태: 정지

        # [수정됨] 단일 트래커 대신 트래커 딕셔너리를 FocusMonitor에 전달
        self.focus_monitor = FocusMonitor(self.trackers, self.paused_event)

        self.gui = SettingsGUI(
            self,  # app_instance
            self.config,
            self.profiles,
            self.trackers,  # 딕셔너리 전달
            self.on_start,
            self.on_stop,
            self.on_hotkey_change,
        )

        self.hotkey = HotkeyManager(
            self.config.get("hotkey", "Ctrl+Shift+E"), self.on_hotkey
        )

        self.tray = TrayManager(
            self.on_pause_toggle, self.on_open_settings, self.on_quit
        )

        # [안전 장치] 어떤 이유로든 프로그램이 종료될 때 cleanup 함수가 실행되도록 등록 (좀비 프로세스 방지)
        atexit.register(self.cleanup)

    def _request_ui_update(self):
        # [안전 장치] GUI가 유효한지 확인 후 메인 루프에서 업데이트 실행
        if self.gui and self.gui.root:
            self.gui.root.after(0, self.gui.update_ui)

    def global_auto_fill(self, excluded_windows=None, is_specific_targets=False):
        """[핵심 로직] 글로벌 스왑 모드일 때 전체 모니터를 대상으로 자동 지정을 수행합니다."""
        import win32gui
        from .win_utils import get_window_list

        if is_specific_targets:
            targets = excluded_windows if excluded_windows else []
        else:
            if excluded_windows is None:
                excluded_windows = []
            windows = get_window_list(None)
            my_hwnd = self.gui.root.winfo_id() if self.gui and self.gui.root else 0
            targets = [
                w[0]
                for w in windows
                if w[0] != my_hwnd
                and "Window Tiler" not in w[1]
                and w[1] not in excluded_windows
            ]

        if not targets:
            return 0

        g_mon = self.config.get("global_main_monitor", 0)
        g_slot = self.config.get("global_main_slot", 0)

        locks = [self.trackers[i].lock for i in sorted(self.trackers.keys())]
        for lock in locks:
            lock.acquire()

        try:
            for tracker in self.trackers.values():
                for s in tracker.slots:
                    if not s.get("locked", False):
                        s["hwnd"] = None

            fill_queue = []
            tracker_main = self.trackers.get(g_mon)

            # 1순위: 글로벌 메인 슬롯
            if tracker_main and g_slot < len(tracker_main.slots):
                fill_queue.append((tracker_main, g_slot))

            # 2순위: 글로벌 메인 모니터의 나머지 슬롯들 (오름차순)
            if tracker_main:
                for i in range(len(tracker_main.slots)):
                    if i != g_slot:
                        fill_queue.append((tracker_main, i))

            # 3순위: 나머지 모니터들의 슬롯들을 모니터 번호 오름차순, 슬롯 번호 오름차순으로 채움 (로컬 메인 무시)
            for mon_idx in sorted(self.trackers.keys()):
                if mon_idx != g_mon:
                    tracker = self.trackers[mon_idx]
                    for i in range(len(tracker.slots)):
                        fill_queue.append((tracker, i))

            count = 0
            # 사용 가능한 창 목록 복사
            available_targets = list(targets)

            # 현재 모든 슬롯에 배정된 창 HWND 수집 (고정 여부와 관계없이)
            assigned_hwnds = set()
            for tracker in self.trackers.values():
                for s in tracker.slots:
                    if s.get("hwnd"):
                        assigned_hwnds.add(s["hwnd"])
            # 이미 배정된 창은 제외 (중복 배정 방지) - targets는 HWND 리스트
            available_targets = [
                w for w in available_targets if w not in assigned_hwnds
            ]

            for tracker, slot_idx in fill_queue:
                if not available_targets:
                    break
                if not tracker.slots[slot_idx].get("locked", False):
                    # 할당할 창을 목록에서 pop
                    hwnd_to_assign = available_targets.pop(0)
                    tracker.slots[slot_idx]["hwnd"] = hwnd_to_assign
                    count += 1

            for tracker in self.trackers.values():
                tracker.reposition_all()

            return count

        finally:
            for lock in reversed(locks):
                lock.release()

    def on_start(self):
        # [핵심 로직] 타일링 활성화
        self.paused_event.clear()
        for tracker in self.trackers.values():
            tracker.is_paused = False
            tracker.refresh_overlays()
        if self.gui:
            self.gui.set_status("타일링 작동 중", "success")

    def on_stop(self):
        # [핵심 로직] 타일링 일시 정지
        self.paused_event.set()
        for tracker in self.trackers.values():
            tracker.is_paused = True
            tracker.refresh_overlays()
        if self.gui:
            self.gui.set_status("일시 정지", "info")

    def on_pause_toggle(self, icon, item):
        if self.paused_event.is_set():
            self.on_start()
        else:
            self.on_stop()

    def on_hotkey_change(self, new_hotkey_str):
        # [위험] 기존 단축키 스레드를 확실히 종료한 후 새 매니저 생성
        if self.hotkey:
            self.hotkey.stop()
        self.hotkey = HotkeyManager(new_hotkey_str, self.on_hotkey)
        self.hotkey.start()
        self.config["hotkey"] = new_hotkey_str
        save_config(self.config)

    def on_hotkey(self):
        """[핵심 로직] 단축키가 눌렸을 때, 현재 스왑 모드에 따라 다르게 작동합니다."""
        swap_mode = self.config.get("swap_mode", "local")

        if swap_mode == "global":
            # 글로벌 모드: 모든 모니터를 한 번에 제어 (전체 시작/중지)
            self.on_pause_toggle(None, None)
        else:
            # 로컬 모드: 기존처럼 활성 창이 있는 모니터만 제어
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    from .win_utils import is_window_in_rect

                    for tracker in self.trackers.values():
                        if tracker.monitor_info and is_window_in_rect(
                            hwnd,
                            (
                                tracker.monitor_info["x"],
                                tracker.monitor_info["y"],
                                tracker.monitor_info["width"],
                                tracker.monitor_info["height"],
                            ),
                        ):
                            # 창이 속한 모니터의 트래커에게 스왑/단축키 액션을 요청
                            self.on_pause_toggle(None, None, target_tracker=tracker)
                            return
            except Exception:
                pass

            # 포커스된 창을 찾지 못했다면 기본(메인 GUI가 보고 있는) 트래커를 제어
            active_tracker = self.trackers.get(self.active_monitor_index)
            if active_tracker:
                self.on_pause_toggle(None, None, target_tracker=active_tracker)

    def on_open_settings(self, icon, item):
        if self.gui and self.gui.root:
            self.gui.root.after(0, self.gui.show)

    def on_pause_toggle(self, icon, item, target_tracker=None):
        # [수정] target_tracker가 명시되면 해당 트래커만 토글, 아니면 전체를 토글
        if target_tracker:
            if self.paused_event.is_set() or target_tracker.is_paused:
                self.paused_event.clear()
                target_tracker.is_paused = False
                target_tracker.refresh_overlays()
            else:
                # 트래커 하나만 멈춘다고 전역 paused_event를 설정하지는 않음 (독립 작동)
                target_tracker.is_paused = True
                target_tracker.refresh_overlays()

            # UI 업데이트 요청 (선택적)
            if self.gui and self.active_monitor_index == target_tracker.monitor_index:
                status = (
                    "타일링 작동 중" if not target_tracker.is_paused else "일시 정지"
                )
                status_type = "success" if not target_tracker.is_paused else "info"
                self.gui.set_status(status, status_type)
        else:
            # 기존 트레이 메뉴를 통한 전체 토글
            if self.paused_event.is_set():
                self.on_start()
            else:
                self.on_stop()

    def cleanup(self):
        """[안전 장치] 모든 백그라운드 자원을 안전하게 해제하는 통합 함수"""
        print("프로그램 종료 중: 리소스 해제...")
        try:
            if hasattr(self, "tray") and self.tray:
                self.tray.stop()
            if hasattr(self, "trackers") and self.trackers:
                for tracker in self.trackers.values():
                    tracker.stop()
            if hasattr(self, "hotkey") and self.hotkey:
                self.hotkey.stop()
            # focus_monitor 등 스레드 객체가 있다면 추가 정지 로직 필요
        except Exception as e:
            print(f"Cleanup 중 오류 발생: {e}")

    def on_quit(self, icon, item):
        # [안전 장치] 사용자 종료 요청 시 cleanup 후 프로세스 종료
        self.cleanup()
        if self.gui:
            self.gui.quit()
        sys.exit(0)

    def handle_global_focus_swap(self, monitor_idx, slot_idx):
        """[핵심 로직] Alt+Tab 등으로 포커스된 창을 글로벌 메인과 스왑합니다."""
        # on_slot_click은 클릭된 슬롯이 타겟이지만, 여기서는 포커스된 슬롯이 타겟입니다. 로직은 동일.
        self.on_slot_click(monitor_idx, slot_idx)

    def on_slot_click(self, monitor_idx, slot_idx):
        """[핵심 로직] 오버레이를 클릭했을 때 로컬 또는 글로벌 스왑을 처리하는 라우터"""
        swap_mode = self.config.get("swap_mode", "local")

        if swap_mode == "global":
            g_mon = self.config.get("global_main_monitor", 0)
            g_slot = self.config.get("global_main_slot", 0)

            # 자기 자신이 글로벌 메인 슬롯이면 무시
            if monitor_idx == g_mon and slot_idx == g_slot:
                return

            tracker_src = self.trackers.get(monitor_idx)
            tracker_dst = self.trackers.get(g_mon)

            if not tracker_src or not tracker_dst:
                return

            # [버그 수정] 같은 모니터 내에서의 글로벌 메인 스왑인 경우, 락을 두 번 얻으려고 하면(Reentrant Lock이 아닐 때) 데드락 발생.
            if monitor_idx == g_mon:
                with tracker_src.lock:
                    slot_src = tracker_src.slots[slot_idx]
                    slot_dst = tracker_src.slots[g_slot]

                    if slot_src.get("locked") or slot_dst.get("locked"):
                        return

                    # 스왑 처리
                    tracker_src.slots[slot_idx], tracker_src.slots[g_slot] = (
                        slot_dst,
                        slot_src,
                    )
                tracker_src.reposition_all()
                self._request_ui_update()
            else:
                # [안전 장치] 데드락(Deadlock) 방지를 위해 항상 인덱스가 작은 모니터부터 락(Lock)을 획득합니다.
                t1, t2 = (
                    (tracker_src, tracker_dst)
                    if monitor_idx < g_mon
                    else (tracker_dst, tracker_src)
                )

                with t1.lock:
                    with t2.lock:
                        slot_src = tracker_src.slots[slot_idx]
                        slot_dst = tracker_dst.slots[g_slot]

                        if slot_src.get("locked") or slot_dst.get("locked"):
                            return

                        # 스왑 처리
                        tracker_src.slots[slot_idx], tracker_dst.slots[g_slot] = (
                            slot_dst,
                            slot_src,
                        )

                tracker_src.reposition_all()
                tracker_dst.reposition_all()
                self._request_ui_update()

        else:
            # 로컬 스왑 (기존 동작)
            tracker = self.trackers.get(monitor_idx)
            if tracker:
                tracker.swap_to_main(slot_idx)

    def run(self):
        # [핵심 로직] 구성 요소 가동 (각 start() 내부 스레드는 daemon=True 권장)
        for tracker in self.trackers.values():
            tracker.start()
        self.focus_monitor.start()
        self.hotkey.start()
        self.tray.start()

        # GUI 표시
        self.gui.show()

        # [이해 포인트] OverlayManager 초기화 및 연동 (각 모니터별로 개별 관리)
        self.overlay_managers = {}
        for idx, tracker in self.trackers.items():
            # [수정] 개별 트래커의 swap_to_main 대신, main.py의 중앙 관리 라우터인 on_slot_click을 연결합니다.
            click_callback = lambda s_idx, m_idx=idx: self.on_slot_click(m_idx, s_idx)
            om = OverlayManager(self.gui.root, click_callback, tracker)
            self.overlay_managers[idx] = om
            tracker.set_overlay_manager(om)
            tracker.refresh_overlays()

        # [핵심 로직] 메인 루프 실행
        self.gui.loop()


def main():
    """메인 실행 함수"""
    try:
        app = WindowTilerApp()
        app.run()
    except Exception:
        # [위험] 예기치 못한 에러 발생 시 로그를 남기고 안전하게 종료 시도
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
