import win32api
import ctypes
from ..app_config import DEFAULT_DPI_SCALE, BASE_DPI

def get_all_monitors():
    monitors = []
    try:
        monitors_data = win32api.EnumDisplayMonitors(None, None)
        for hmonitor, hdc, rect in monitors_data:
            r = win32api.GetMonitorInfo(hmonitor)
            work_rect = r["Work"]
            monitors.append(
                {
                    "handle": hmonitor,
                    "rect": r["Monitor"],
                    "work": work_rect,
                    "name": r.get("Device", f"Monitor {len(monitors)}"),
                    "width": work_rect[2] - work_rect[0],
                    "height": work_rect[3] - work_rect[1],
                    "x": work_rect[0],
                    "y": work_rect[1],
                }
            )
    except Exception as e:
        print(f"Error enumerating monitors: {e}")
    return monitors

def get_monitor_info(index=0):
    monitors = get_all_monitors()
    if not monitors:
        return None
    if index < len(monitors):
        return monitors[index]
    return monitors[0]

def get_monitor_dpi_scale(hmonitor):
    try:
        dpiX = ctypes.c_uint()
        dpiY = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(
            int(hmonitor), 0, ctypes.byref(dpiX), ctypes.byref(dpiY)
        )
        return dpiX.value / BASE_DPI
    except Exception:
        return DEFAULT_DPI_SCALE

def get_monitor_dpi_scale_by_hwnd(hwnd):
    try:
        MONITOR_DEFAULTTONEAREST = 2
        hmonitor = win32api.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        return get_monitor_dpi_scale(hmonitor)
    except Exception:
        return DEFAULT_DPI_SCALE
