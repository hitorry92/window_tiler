import ctypes
import ctypes.wintypes
import threading
from . import win_utils

# Win32 Constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

class FocusMonitor:
    def __init__(self, tracker, paused_event):
        self.tracker = tracker # 단일 WindowTracker 인스턴스
        self.paused_event = paused_event
        self.hook = None
        self.thread = None

    def _callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        if self.paused_event.is_set(): return
        if event == EVENT_SYSTEM_FOREGROUND and hwnd:
            self.tracker.on_focus_event(hwnd)

    def start(self):
        def run():
            WINEVENTPROC = ctypes.WINFUNCTYPE(None, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.HWND, ctypes.wintypes.LONG, ctypes.wintypes.LONG, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)
            self.proc = WINEVENTPROC(self._callback)
            self.hook = ctypes.windll.user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, None, self.proc, 0, 0, WINEVENT_OUTOFCONTEXT)
            
            msg = ctypes.wintypes.MSG()
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
