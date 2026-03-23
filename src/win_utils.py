import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes

def get_all_monitors():
    monitors = []
    # pywin32의 win32api.EnumDisplayMonitors는 (None, None) 호출 시 모니터 목록을 리스트로 반환함
    try:
        monitors_data = win32api.EnumDisplayMonitors(None, None)
        for hmonitor, hdc, rect in monitors_data:
            r = win32api.GetMonitorInfo(hmonitor)
            work_rect = r["Work"]
            monitors.append({
                "handle": hmonitor,
                "rect": r["Monitor"],
                "work": work_rect,
                "name": r.get("Device", f"Monitor {len(monitors)}"),
                "width": work_rect[2] - work_rect[0],
                "height": work_rect[3] - work_rect[1],
                "x": work_rect[0],
                "y": work_rect[1]
            })
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

def is_valid_window(hwnd):
    """현재 윈도우가 실제 배치 가능한 유효한 창인지 상세 검사 (Cycle 15 강화)"""
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False
    
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False
        
    try:
        # 1. 윈도우 크기 체크 (너무 작은 시스템 창 제외)
        rect = win32gui.GetWindowRect(hwnd)
        if (rect[2] - rect[0]) < 10 or (rect[3] - rect[1]) < 10:
            return False

        # 2. DWM Cloaked 상태 체크 (유령 창 필터링 핵심)
        # 윈도우 10/11 UWP 앱(설정 등)은 화면에 안 보여도 Visible인 경우가 많음
        cloaked = ctypes.c_int(0)
        DWMWA_CLOAKED = 14
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        if cloaked.value != 0:
            return False

        # 3. 클래스 및 스타일 체크
        class_name = win32gui.GetClassName(hwnd)
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # 3.1 소유주가 있는 창 제외 (대부분의 팝업/대화상자는 소유주가 있음)
        owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        if owner != 0:
            return False

        # 3.2 크기 조절이 불가능한 창 제외 (대화상자, 고정 팝업 등)
        if not (style & win32con.WS_THICKFRAME):
            return False

        # 자신의 GUI 창 제외
        if class_name in ["Tk", "TkTopLevel"] and "Window Tiler" in title:
            return False
            
        # Tool windows 제외
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return False
            
        # 바탕화면 및 태스크바 등 제외
        if class_name in ["Progman", "WorkerW", "Shell_TrayWnd", "NotifyIconOverflowWindow"]:
            return False
            
    except Exception:
        # 오류 발생 시 안전을 위해 제외
        return False
        
    return True

def is_window_in_rect(hwnd, target_rect):
    """창의 중심이 해당 사각형 영역 내에 있는지 확인"""
    try:
        rect = win32gui.GetWindowRect(hwnd)
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        x, y, w, h = target_rect
        return x <= cx < x + w and y <= cy < y + h
    except Exception:
        return False

def get_window_margin(hwnd):
    """윈도우의 투명 테두리(Shadow 등)로 인한 마진을 계산 (Cycle 15)"""
    try:
        rect = win32gui.GetWindowRect(hwnd)
        f_rect = wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, 
            ctypes.byref(f_rect), ctypes.sizeof(f_rect)
        )
        return (
            f_rect.left - rect[0],   # left margin
            f_rect.top - rect[1],    # top margin (shadow)
            rect[2] - f_rect.right,  # right margin
            rect[3] - f_rect.bottom  # bottom margin
        )
    except Exception:
        return (0, 0, 0, 0)

def move_window_precision(hwnd, x, y, w, h):
    """DWM 확장 프레임 보정을 포함하되, 안전장치를 강화한 정밀 배치 (Cycle 15)"""
    # 1. 창 상태 확인: 최대화되어 있다면 먼저 복구
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMAXIMIZED:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        # 윈도우 애니메이션 대기 (필요 시)
    
    margin = get_window_margin(hwnd)
    
    # 2. 보정값 유효성 검사: 0~20px 사이의 합리적인 마진일 때만 보정 적용
    # 그 외의 경우(그림자 없음, 특수 창 등) 보정 없이 진행
    is_sane = all(0 <= v <= 20 for v in margin)
    
    if is_sane:
        new_x, new_y = x - margin[0], y - margin[1]
        new_w, new_h = w + margin[0] + margin[2], h + margin[1] + margin[3]
    else:
        new_x, new_y, new_w, new_h = x, y, w, h
    
    flags = win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED | win32con.SWP_NOZORDER
    win32gui.SetWindowPos(hwnd, 0, new_x, new_y, new_w, new_h, flags)

def get_window_list(monitor_info=None):
    windows = []
    def callback(hwnd, _):
        if is_valid_window(hwnd):
            if not monitor_info or is_window_in_rect(hwnd, (monitor_info["x"], monitor_info["y"], monitor_info["width"], monitor_info["height"])):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True
    
    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda x: x[1].lower())
    return windows
