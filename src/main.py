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

        mon_idx = self.config.get("monitor_index", 0)

        # [위험] 메인 컨트롤러와 엔진 간의 순환 참조나 초기화 순서 주의
        self.tracker = WindowTracker(
            mon_idx,
            self.profiles,
            self.config,
            ui_update_callback=self._request_ui_update,
        )

        self.paused_event = threading.Event()
        self.paused_event.set()  # 초기 상태: 정지

        self.focus_monitor = FocusMonitor(self.tracker, self.paused_event)

        self.gui = SettingsGUI(
            self.config,
            self.profiles,
            self.tracker,
            self.on_start,
            self.on_stop,
            self.on_hotkey_change,
        )

        self.hotkey = HotkeyManager(
            self.config.get("hotkey", "Ctrl+Shift+T"), self.on_hotkey
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

    def on_start(self):
        # [핵심 로직] 타일링 활성화
        self.paused_event.clear()
        self.tracker.is_paused = False
        self.tracker.refresh_overlays()
        if self.gui:
            self.gui.set_status("타일링 작동 중", "success")

    def on_stop(self):
        # [핵심 로직] 타일링 일시 정지
        self.paused_event.set()
        self.tracker.is_paused = True
        self.tracker.refresh_overlays()
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
        self.on_pause_toggle(None, None)

    def on_open_settings(self, icon, item):
        if self.gui and self.gui.root:
            self.gui.root.after(0, self.gui.show)

    def cleanup(self):
        """[안전 장치] 모든 백그라운드 자원을 안전하게 해제하는 통합 함수"""
        print("프로그램 종료 중: 리소스 해제...")
        try:
            if hasattr(self, "tray") and self.tray:
                self.tray.stop()
            if hasattr(self, "tracker") and self.tracker:
                self.tracker.stop()
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

    def run(self):
        # [핵심 로직] 구성 요소 가동 (각 start() 내부 스레드는 daemon=True 권장)
        self.tracker.start()
        self.focus_monitor.start()
        self.hotkey.start()
        self.tray.start()

        # GUI 표시
        self.gui.show()

        # [이해 포인트] OverlayManager 초기화 및 연동
        self.overlay_manager = OverlayManager(
            self.gui.root, self.tracker.swap_to_main, self.tracker
        )
        self.tracker.set_overlay_manager(self.overlay_manager)
        self.tracker.refresh_overlays()

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
