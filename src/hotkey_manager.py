import win32con
import win32api
import threading
import ctypes
from ctypes import wintypes


class HotkeyManager:
    # [이해 포인트] 사용자가 지정한 단축키 문자열("ctrl+alt+t" 등)과 눌렸을 때 실행할 함수(콜백)를 받아서 초기화합니다.
    def __init__(self, hotkey_str, on_press_callback):
        self.hotkey_str = hotkey_str
        self.callback = on_press_callback
        # [핵심 로직] 문자열로 된 단축키를 윈도우 API가 이해할 수 있는 형태(조합키, 가상키)로 변환합니다.
        self.modifiers, self.vk = self._parse_hotkey(hotkey_str)
        # [안전 장치] 스레드를 안전하게 종료하기 위한 이벤트 객체입니다.
        self._stop_event = threading.Event()
        self.thread = None
        self.hotkey_id = None

    # [핵심 로직] 단축키 문자열을 분석하여 조합키(modifiers)와 가상키 코드(vk)를 반환하는 함수입니다.
    def _parse_hotkey(self, hotkey_str):
        modifiers = 0
        vk = 0
        # [이해 포인트] "ctrl+alt+a" 같은 문자열을 '+' 기준으로 쪼개서 리스트로 만듭니다.
        parts = hotkey_str.lower().split("+")

        # [이해 포인트] 자주 사용하는 특수 키들의 윈도우 가상 키 코드를 미리 매핑해둡니다.
        vk_map = {
            "f1": win32con.VK_F1,
            "f2": win32con.VK_F2,
            "f3": win32con.VK_F3,
            "f4": win32con.VK_F4,
            "f5": win32con.VK_F5,
            "f6": win32con.VK_F6,
            "f7": win32con.VK_F7,
            "f8": win32con.VK_F8,
            "f9": win32con.VK_F9,
            "f10": win32con.VK_F10,
            "f11": win32con.VK_F11,
            "f12": win32con.VK_F12,
            "space": win32con.VK_SPACE,
            "enter": win32con.VK_RETURN,
            "tab": win32con.VK_TAB,
            "esc": win32con.VK_ESCAPE,
            "escape": win32con.VK_ESCAPE,
            "left": win32con.VK_LEFT,
            "right": win32con.VK_RIGHT,
            "up": win32con.VK_UP,
            "down": win32con.VK_DOWN,
            "insert": win32con.VK_INSERT,
            "delete": win32con.VK_DELETE,
            "home": win32con.VK_HOME,
            "end": win32con.VK_END,
            "pgup": win32con.VK_PRIOR,
            "pgdn": win32con.VK_NEXT,
        }

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # [이해 포인트] 조합키(ctrl, shift, alt, win)인 경우 비트 연산자(|)를 사용해 modifiers 값을 누적합니다.
            if part == "ctrl":
                modifiers |= win32con.MOD_CONTROL
            elif part == "shift":
                modifiers |= win32con.MOD_SHIFT
            elif part == "alt":
                modifiers |= win32con.MOD_ALT
            elif part == "win":
                modifiers |= win32con.MOD_WIN
            elif part in vk_map:
                vk = vk_map[part]
            elif len(part) == 1:
                # Fix: Use VkKeyScan to correctly get the virtual key code for characters
                # [핵심 로직] 일반 문자(a, b, c 등)인 경우 VkKeyScan API를 사용하여 해당하는 가상 키 코드를 찾습니다.
                result = win32api.VkKeyScan(part)
                if result == -1:
                    print(f"Warning: Could not find key: {part}")
                else:
                    vk = result & 0xFF

        return modifiers, vk

    # [핵심 로직] 백그라운드에서 단축키 입력을 감지할 수 있도록 새로운 스레드를 시작합니다.
    def start(self):
        self._stop_event.clear()
        # [안전 장치] daemon=True로 설정하여 메인 프로그램이 종료될 때 이 스레드도 함께 종료되도록 합니다.
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        # Fix: Use GlobalAddAtom for a unique, collision-free hotkey ID
        # [핵심 로직] 다른 프로그램이나 단축키와 충돌하지 않도록 고유한 단축키 ID(Atom)를 생성합니다.
        hotkey_name = f"WinTiler_{self.hotkey_str}_{threading.get_ident()}"
        self.hotkey_id = ctypes.windll.kernel32.GlobalAddAtomW(hotkey_name)

        # [안전 장치] ID 생성에 실패하면 오류 메시지를 출력하고 함수를 종료합니다.
        if not self.hotkey_id:
            print(f"Failed to create a unique ID for hotkey: {self.hotkey_str}")
            return

        # [위험] 단축키가 다른 프로그램에서 이미 사용 중이면 등록에 실패할 수 있습니다.
        if not ctypes.windll.user32.RegisterHotKey(
            None, self.hotkey_id, self.modifiers, self.vk
        ):
            print(
                f"Failed to register hotkey: {self.hotkey_str} (It is likely in use by another program)"
            )
            # [안전 장치] 등록 실패 시 생성했던 고유 ID(Atom)를 삭제하여 메모리 누수를 방지합니다.
            ctypes.windll.kernel32.GlobalDeleteAtom(self.hotkey_id)
            return

        try:
            msg = wintypes.MSG()
            # [이해 포인트] 스레드가 종료되기 전까지 무한 반복하며 윈도우 메시지를 기다립니다.
            while not self._stop_event.is_set():
                # [핵심 로직] GetMessageW를 통해 시스템으로부터 단축키 입력 메시지를 가져옵니다.
                if ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    # [이해 포인트] 도착한 메시지가 단축키 입력(WM_HOTKEY)이고, 우리가 등록한 단축키 ID와 일치하는지 확인합니다.
                    if msg.message == win32con.WM_HOTKEY:
                        if msg.wParam == self.hotkey_id:
                            # [핵심 로직] 단축키가 눌렸으므로 초기화할 때 전달받았던 콜백 함수를 실행합니다.
                            self.callback()
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            # [안전 장치] 스레드가 종료될 때 등록했던 단축키를 해제하고, 생성했던 고유 ID도 삭제합니다.
            ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)
            ctypes.windll.kernel32.GlobalDeleteAtom(self.hotkey_id)

    # [핵심 로직] 단축키 감지 스레드를 안전하게 중지시키는 함수입니다.
    def stop(self):
        # [이해 포인트] 종료 이벤트를 설정하여 _run 함수의 무한 루프가 끝날 수 있게 합니다.
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            # Post a dummy message to wake up the GetMessageW loop
            # [위험] GetMessageW는 메시지가 올 때까지 스레드를 멈추고 대기(Blocking)합니다.
            # [안전 장치] 빈 메시지(WM_NULL)를 강제로 보내 대기 상태를 풀고 스레드가 정상 종료되도록 깨웁니다.
            ctypes.windll.user32.PostThreadMessageW(
                self.thread.ident, win32con.WM_NULL, 0, 0
            )
            self.thread.join(timeout=1)
