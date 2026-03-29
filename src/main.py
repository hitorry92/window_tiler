# -*- coding: utf-8 -*-
import sys
import threading
import ctypes
import traceback
import atexit  # [안전 장치] 프로그램 비정상 종료 시에도 리소스 해제를 보장하기 위해 추가
from threading import Event
from .app_config import (
    load_config,
    load_profiles,
    save_config,
    DEFAULT_SWAP_MODE,
    DEFAULT_PROFILE,
)
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
                    "profile": DEFAULT_PROFILE,
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

            # [프로필] 프로필에 저장된 slot_states (고정, 덮개) 복원
            profile_name = mon_config.get("profile", DEFAULT_PROFILE)
            profile = self.profiles.get(
                profile_name, self.profiles.get(DEFAULT_PROFILE, {})
            )
            slot_states = profile.get("slot_states", {})
            if slot_states and tracker.slots:
                for idx, slot in enumerate(tracker.slots):
                    state = slot_states.get(str(idx), {})
                    slot["locked"] = state.get("locked", False)
                    slot["overlay_enabled"] = state.get("overlay_enabled", True)

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
        """[리팩토링] GlobalWindowManager로 로직 위임"""
        from .core.global_window_manager import GlobalWindowManager

        if not hasattr(self, "global_window_manager"):
            self.global_window_manager = GlobalWindowManager(self)
        return self.global_window_manager.auto_fill(
            excluded_windows, is_specific_targets
        )

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
        swap_mode = self.config.get("swap_mode", DEFAULT_SWAP_MODE)

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
        """[리팩토링] GlobalWindowManager로 로직 위임"""
        self.on_slot_click(monitor_idx, slot_idx)

    def on_slot_click(self, monitor_idx, slot_idx):
        """[리팩토링] GlobalWindowManager로 로직 위임"""
        from .core.global_window_manager import GlobalWindowManager

        if not hasattr(self, "global_window_manager"):
            self.global_window_manager = GlobalWindowManager(self)

        swap_mode = self.config.get("swap_mode", DEFAULT_SWAP_MODE)
        if swap_mode == "global":
            self.global_window_manager.handle_global_swap(monitor_idx, slot_idx)
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
