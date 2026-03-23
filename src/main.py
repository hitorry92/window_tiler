# -*- coding: utf-8 -*-
import sys
import threading
import ctypes
import traceback
from threading import Event
from .app_config import load_config, load_profiles, save_config
from .win_utils import get_all_monitors
from .tiling_engine import WindowTracker
from .event_monitor import FocusMonitor
from .hotkey_manager import HotkeyManager
from .tray_manager import TrayManager
from .settings_gui import SettingsGUI
from .overlay_manager import OverlayManager

# 프로세스 DPI 인식 설정 (고해상도 모니터 대응)
try:
    # Per-Monitor V2가 가장 높은 수준의 DPI 인식을 제공
    ctypes.windll.shcore.SetProcessDpiAwarenessContext(
        -4
    )  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
except (AttributeError, TypeError):
    # 구형 Windows와의 호환성을 위해 대체 방법 시도
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class WindowTilerApp:
    def __init__(self):
        self.config = load_config()
        self.profiles = load_profiles()

        # 단입 트래커 생성
        mon_idx = self.config.get("monitor_index", 0)
        self.tracker = WindowTracker(
            mon_idx,
            self.profiles,
            self.config,
            ui_update_callback=lambda: self.gui.root.after(0, self.gui.update_ui),
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

    def on_start(self):
        self.paused_event.clear()
        self.tracker.is_paused = False
        self.tracker.refresh_overlays()
        self.gui.set_status("타일링 작동 중", "success")

    def on_stop(self):
        self.paused_event.set()
        self.tracker.is_paused = True
        self.tracker.refresh_overlays()
        self.gui.set_status("일시 정지", "info")

    def on_pause_toggle(self, icon, item):
        if self.paused_event.is_set():
            self.on_start()
        else:
            self.on_stop()

    def on_hotkey_change(self, new_hotkey_str):
        self.hotkey.stop()
        self.hotkey = HotkeyManager(new_hotkey_str, self.on_hotkey)
        self.hotkey.start()
        self.config["hotkey"] = new_hotkey_str
        save_config(self.config)

    def on_hotkey(self):
        self.on_pause_toggle(None, None)

    def on_open_settings(self, icon, item):
        self.gui.root.after(0, self.gui.root.deiconify)

    def on_quit(self, icon, item):
        self.tray.stop()
        self.tracker.stop()  # 주기적 체크 스레드 중지
        self.gui.quit()
        sys.exit(0)

    def run(self):
        self.tracker.start()  # 주기적 체크 스레드 시작
        self.focus_monitor.start()
        self.hotkey.start()
        self.tray.start()
        self.gui.show()  # root 초기화 및 UI 생성

        # OverlayManager 초기화 및 연동
        self.overlay_manager = OverlayManager(self.gui.root, self.tracker.swap_to_main)
        self.tracker.set_overlay_manager(self.overlay_manager)
        self.tracker.refresh_overlays()

        self.gui.loop()  # mainloop 실행


def main():
    """메인 실행 함수"""
    app = WindowTilerApp()
    app.run()


if __name__ == "__main__":
    # main() -> if __name__ == "__main__" 블록으로 이동
    main()
