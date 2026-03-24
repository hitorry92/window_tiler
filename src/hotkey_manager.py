import win32con
import win32api
import threading
import ctypes
from ctypes import wintypes


class HotkeyManager:
    def __init__(self, hotkey_str, on_press_callback):
        self.hotkey_str = hotkey_str
        self.callback = on_press_callback
        self.modifiers, self.vk = self._parse_hotkey(hotkey_str)
        self._stop_event = threading.Event()
        self.thread = None
        self.hotkey_id = None

    def _parse_hotkey(self, hotkey_str):
        modifiers = 0
        vk = 0
        parts = hotkey_str.lower().split("+")

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
                result = win32api.VkKeyScan(part)
                if result == -1:
                    print(f"Warning: Could not find key: {part}")
                else:
                    vk = result & 0xFF

        return modifiers, vk

    def start(self):
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        # Fix: Use GlobalAddAtom for a unique, collision-free hotkey ID
        hotkey_name = f"WinTiler_{self.hotkey_str}_{threading.get_ident()}"
        self.hotkey_id = ctypes.windll.kernel32.GlobalAddAtomW(hotkey_name)

        if not self.hotkey_id:
            print(f"Failed to create a unique ID for hotkey: {self.hotkey_str}")
            return

        if not ctypes.windll.user32.RegisterHotKey(
            None, self.hotkey_id, self.modifiers, self.vk
        ):
            print(
                f"Failed to register hotkey: {self.hotkey_str} (It is likely in use by another program)"
            )
            ctypes.windll.kernel32.GlobalDeleteAtom(self.hotkey_id)
            return

        try:
            msg = wintypes.MSG()
            while not self._stop_event.is_set():
                if ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == win32con.WM_HOTKEY:
                        if msg.wParam == self.hotkey_id:
                            self.callback()
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)
            ctypes.windll.kernel32.GlobalDeleteAtom(self.hotkey_id)

    def stop(self):
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            # Post a dummy message to wake up the GetMessageW loop
            ctypes.windll.user32.PostThreadMessageW(
                self.thread.ident, win32con.WM_NULL, 0, 0
            )
            self.thread.join(timeout=1)
