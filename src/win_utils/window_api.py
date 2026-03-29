import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes
from .window_filter import is_valid_window, is_window_in_rect

def get_window_margin(hwnd):
    try:
        rect = win32gui.GetWindowRect(hwnd)
        f_rect = wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(f_rect),
            ctypes.sizeof(f_rect),
        )
        return (
            f_rect.left - rect[0],
            f_rect.top - rect[1],
            rect[2] - f_rect.right,
            rect[3] - f_rect.bottom,
        )
    except Exception:
        return (0, 0, 0, 0)

def move_window_precision(hwnd, x, y, w, h):
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMAXIMIZED:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    margin = get_window_margin(hwnd)
    is_sane = all(0 <= v <= 20 for v in margin)

    if is_sane:
        new_x, new_y = x - margin[0], y - margin[1]
        new_w, new_h = w + margin[0] + margin[2], h + margin[1] + margin[3]
    else:
        new_x, new_y, new_w, new_h = x, y, w, h

    move_flags = win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER | win32con.SWP_NOSIZE
    win32gui.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0, move_flags)

    size_flags = (
        win32con.SWP_NOACTIVATE
        | win32con.SWP_FRAMECHANGED
        | win32con.SWP_NOZORDER
        | win32con.SWP_NOMOVE
    )
    win32gui.SetWindowPos(hwnd, 0, 0, 0, new_w, new_h, size_flags)

def get_window_list(monitor_info=None):
    windows = []

    def callback(hwnd, _):
        if is_valid_window(hwnd):
            if not monitor_info or is_window_in_rect(
                hwnd,
                (
                    monitor_info["x"],
                    monitor_info["y"],
                    monitor_info["width"],
                    monitor_info["height"],
                ),
            ):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True

    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda x: x[1].lower())
    return windows
