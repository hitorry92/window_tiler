import win32gui
import win32con
import ctypes
from ..app_config import APP_NAME

def is_own_window(title):
    return title.strip() == APP_NAME

def is_valid_window(hwnd):
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False

    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False

    try:
        rect = win32gui.GetWindowRect(hwnd)
        if (rect[2] - rect[0]) < 10 or (rect[3] - rect[1]) < 10:
            return False

        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if style & win32con.WS_MINIMIZE:
            return False

        cloaked = ctypes.c_int(0)
        DWMWA_CLOAKED = 14
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        if cloaked.value != 0:
            return False

        class_name = win32gui.GetClassName(hwnd)
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        if owner != 0:
            return False

        if not (style & win32con.WS_THICKFRAME):
            return False

        if class_name in ["Tk", "TkTopLevel"] and is_own_window(title):
            return False

        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return False

        if class_name in [
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "NotifyIconOverflowWindow",
        ]:
            return False

    except Exception:
        return False

    return True

def is_window_in_rect(hwnd, target_rect):
    try:
        rect = win32gui.GetWindowRect(hwnd)
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        x, y, w, h = target_rect
        return x <= cx < x + w and y <= cy < y + h
    except Exception:
        return False
