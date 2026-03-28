import ctypes
import ctypes.wintypes
import threading
from . import win_utils

# [이해 포인트] Windows API에서 사용하는 상수로, 포그라운드(활성) 창이 변경될 때 발생하는 이벤트를 나타냅니다.
# Win32 Constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000


class FocusMonitor:
    def __init__(self, trackers_dict, paused_event):
        self.trackers_dict = trackers_dict  # 모니터 인덱스별 WindowTracker 딕셔너리
        # [안전 장치] 외부에서 모니터링을 안전하게 일시정지/재개할 수 있도록 스레드 이벤트 객체를 사용합니다.
        self.paused_event = paused_event
        self.hook = None
        self.thread = None

    # [핵심 로직] 윈도우에서 포그라운드 창이 바뀔 때마다 운영체제에 의해 자동으로 호출되는 콜백 함수입니다.
    def _callback(
        self,
        hWinEventHook,
        event,
        hwnd,
        idObject,
        idChild,
        dwEventThread,
        dwmsEventTime,
    ):
        # [안전 장치] paused_event가 설정(set)되어 있다면, 처리를 중단하여 불필요한 연산과 자원 소모를 막습니다.
        if self.paused_event.is_set():
            return

        # [이해 포인트] 발생한 이벤트가 포그라운드 창 변경 이벤트인지, 그리고 창 핸들(hwnd)이 유효한지 확인합니다.
        if event == EVENT_SYSTEM_FOREGROUND and hwnd:
            # 창이 위치한 모니터 찾기
            try:
                # [핵심 로직] 창 중앙 좌표가 위치한 모니터를 판별합니다.
                from .win_utils import is_window_in_rect

                # 모든 트래커를 순회하며 해당 창을 가지고 있는 (또는 영역 안에 있는) 트래커에게 이벤트를 전달합니다.
                # 각 트래커 내부의 on_focus_event에서도 유효성 검사를 하므로 안전합니다.
                for tracker in self.trackers_dict.values():
                    tracker.on_focus_event(hwnd)
            except Exception as e:
                pass

    def start(self):
        # [이해 포인트] 윈도우 메시지 루프가 메인 스레드를 블로킹(멈춤)하지 않도록 별도의 백그라운드 스레드에서 실행되는 함수입니다.
        def run():
            # [위험] C언어 스타일의 함수 포인터 타입 정의입니다. 인자 타입이 하나라도 틀리면 프로그램이 심각한 오류와 함께 강제 종료될 수 있습니다.
            WINEVENTPROC = ctypes.WINFUNCTYPE(
                None,
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LONG,
                ctypes.wintypes.LONG,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD,
            )

            # [이해 포인트] 파이썬 메서드(_callback)를 Windows API가 호출할 수 있는 C 콜백 함수 형태로 변환합니다.
            self.proc = WINEVENTPROC(self._callback)

            # [핵심 로직] 운영체제에 전역 훅(Hook)을 등록하여 시스템 포그라운드 변경 이벤트를 가로채도록 설정합니다.
            self.hook = ctypes.windll.user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND,
                EVENT_SYSTEM_FOREGROUND,
                None,
                self.proc,
                0,
                0,
                WINEVENT_OUTOFCONTEXT,
            )

            # [핵심 로직] 윈도우 메시지를 수신하는 무한 대기 루프입니다. 이 루프가 있어야 운영체제 콜백 함수가 정상적으로 이벤트를 받을 수 있습니다.
            msg = ctypes.wintypes.MSG()
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        # [안전 장치] daemon=True 옵션을 주어 메인 프로세스 종료 시 모니터링 스레드가 고아(orphan) 상태로 남지 않고 함께 즉시 종료되도록 합니다.
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
