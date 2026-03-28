import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes


# [핵심 로직] 연결된 모든 모니터의 해상도 및 작업 영역 정보를 가져오는 함수입니다.
def get_all_monitors():
    monitors = []
    # pywin32의 win32api.EnumDisplayMonitors는 (None, None) 호출 시 모니터 목록을 리스트로 반환함
    try:
        # [이해 포인트] 현재 시스템에 연결된 모든 디스플레이 모니터를 순회합니다.
        monitors_data = win32api.EnumDisplayMonitors(None, None)
        for hmonitor, hdc, rect in monitors_data:
            # [이해 포인트] 각 모니터의 상세 정보(전체 크기, 작업 영역 등)를 조회합니다.
            r = win32api.GetMonitorInfo(hmonitor)
            # [이해 포인트] 'Work'는 작업 표시줄(Taskbar)을 제외한 실제 창이 뜰 수 있는 영역입니다.
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
        # [안전 장치] 모니터 정보를 가져오다 실패해도 프로그램이 중단되지 않도록 예외를 처리합니다.
        print(f"Error enumerating monitors: {e}")
    return monitors


def get_monitor_info(index=0):
    # [안전 장치] 모니터 목록이 비어있거나, 요청한 인덱스가 범위를 벗어날 경우를 대비한 방어 코드입니다.
    monitors = get_all_monitors()
    if not monitors:
        return None
    if index < len(monitors):
        return monitors[index]
    return monitors[0]


# [핵심 로직] 해당 윈도우(창)가 화면에 보이고 제어 가능한 "실제 창"인지 판별합니다.
def is_valid_window(hwnd):
    """현재 윈도우가 실제 배치 가능한 유효한 창인지 상세 검사 (Cycle 15 강화)"""
    # [이해 포인트] 창이 존재하지 않거나, 화면에 숨겨져(Invisible) 있으면 제외합니다.
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False

    # [이해 포인트] 창 제목이 없는 경우 보통 백그라운드 시스템 프로세스이므로 제외합니다.
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False

    try:
        # 1. 윈도우 크기 체크 (너무 작은 시스템 창 제외)
        # [이해 포인트] 10x10 픽셀보다 작은 창은 정상적인 프로그램 창이 아닐 확률이 높습니다.
        rect = win32gui.GetWindowRect(hwnd)
        if (rect[2] - rect[0]) < 10 or (rect[3] - rect[1]) < 10:
            return False

        # 1.5 최소화된 창 체크 (Minimized 창 필터링)
        # [이해 포인트] 사용자가 작업표시줄로 내려놓은 창(최소화)은 화면 자동 배정에서 제외합니다.
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if style & win32con.WS_MINIMIZE:
            return False

        # 2. DWM Cloaked 상태 체크 (유령 창 필터링 핵심)
        # 윈도우 10/11 UWP 앱(설정 등)은 화면에 안 보여도 Visible인 경우가 많음
        # [위험] 이 검사를 누락하면 화면에 보이지 않는 백그라운드 앱들(유령 창)까지 목록에 포함될 수 있습니다.
        cloaked = ctypes.c_int(0)
        DWMWA_CLOAKED = 14
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        if cloaked.value != 0:
            return False

        # 3. 클래스 및 스타일 체크
        # [이해 포인트] 창의 속성(스타일)을 확인하여 팝업, 대화상자, 툴바 등을 걸러냅니다.
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
        if class_name in [
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "NotifyIconOverflowWindow",
        ]:
            return False

    except Exception:
        # [안전 장치] 권한 문제 등으로 창 정보를 읽다가 오류가 발생하면, 안전하게 무시(False 반환)합니다.
        return False

    return True


# [핵심 로직] 특정 창의 중심이 지정된 모니터(사각형 영역) 안에 위치하는지 검사합니다.
def is_window_in_rect(hwnd, target_rect):
    """창의 중심이 해당 사각형 영역 내에 있는지 확인"""
    try:
        # [이해 포인트] 창의 중심 좌표(cx, cy)를 계산하여, 타겟 영역 안에 들어오는지 판별합니다.
        rect = win32gui.GetWindowRect(hwnd)
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        x, y, w, h = target_rect
        return x <= cx < x + w and y <= cy < y + h
    except Exception:
        # [안전 장치] 창이 닫히는 등의 이유로 좌표를 구할 수 없으면 False를 반환합니다.
        return False


# [핵심 로직] 특정 모니터 핸들(hmonitor)을 받아 DPI 스케일 비율을 반환합니다.
def get_monitor_dpi_scale(hmonitor):
    """주어진 모니터 핸들의 DPI 스케일 비율(예: 1.0, 1.5)을 반환합니다."""
    try:
        dpiX = ctypes.c_uint()
        dpiY = ctypes.c_uint()
        # MDT_EFFECTIVE_DPI = 0
        ctypes.windll.shcore.GetDpiForMonitor(
            int(hmonitor), 0, ctypes.byref(dpiX), ctypes.byref(dpiY)
        )
        return dpiX.value / 96.0
    except Exception:
        return 1.0


# [핵심 로직] 특정 윈도우가 현재 위치한 모니터의 DPI 스케일 비율을 반환합니다.
def get_monitor_dpi_scale_by_hwnd(hwnd):
    """주어진 윈도우가 위치한 모니터의 DPI 스케일 비율(예: 1.0, 1.5)을 반환합니다."""
    try:
        MONITOR_DEFAULTTONEAREST = 2
        hmonitor = win32api.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        return get_monitor_dpi_scale(hmonitor)
    except Exception:
        # 실패 시 기본 배율 100% (1.0) 가정
        return 1.0


# [이해 포인트] 윈도우 10/11의 보이지 않는 그림자(Shadow) 두께를 계산합니다.
def get_window_margin(hwnd):
    """윈도우의 투명 테두리(Shadow 등)로 인한 마진을 계산 (Cycle 15)"""
    try:
        # [핵심 로직] GetWindowRect(전체 영역)와 DwmGetWindowAttribute(실제 프레임 영역)의 차이를 구합니다.
        rect = win32gui.GetWindowRect(hwnd)
        f_rect = wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        # [위험] ctypes를 통한 C++ API 직접 호출이므로, 매개변수 타입이 정확해야 메모리 오류를 피할 수 있습니다.
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(f_rect),
            ctypes.sizeof(f_rect),
        )
        return (
            f_rect.left - rect[0],  # left margin
            f_rect.top - rect[1],  # top margin (shadow)
            rect[2] - f_rect.right,  # right margin
            rect[3] - f_rect.bottom,  # bottom margin
        )
    except Exception:
        # [안전 장치] 계산에 실패하면 마진이 없는 것(0)으로 간주합니다.
        return (0, 0, 0, 0)


# [핵심 로직] 그림자 두께를 고려하여 윈도우 창을 화면의 정확한 위치로 이동시킵니다.
def move_window_precision(hwnd, x, y, w, h):
    """DWM 확장 프레임 보정을 포함하되, 안전장치를 강화한 정밀 배치 (Cycle 15)"""
    # 1. 창 상태 확인: 최대화되어 있다면 먼저 복구
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMAXIMIZED:
        # [안전 장치] 최대화된 상태에서는 위치 변경이 안 될 수 있으므로, 기본 크기로 되돌립니다(RESTORE).
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        # 윈도우 애니메이션 대기 (필요 시)

    margin = get_window_margin(hwnd)

    # 2. 보정값 유효성 검사: 0~20px 사이의 합리적인 마진일 때만 보정 적용
    # 그 외의 경우(그림자 없음, 특수 창 등) 보정 없이 진행
    # [안전 장치] 비정상적인 마진 값으로 인해 창이 엉뚱한 곳으로 튕겨나가는 것을 방지합니다.
    is_sane = all(0 <= v <= 20 for v in margin)

    if is_sane:
        # [이해 포인트] 마진(그림자 영역)을 뺀 위치와 더한 크기로 배치해야 시각적으로 정확한 위치에 맞습니다.
        new_x, new_y = x - margin[0], y - margin[1]
        new_w, new_h = w + margin[0] + margin[2], h + margin[1] + margin[3]
    else:
        new_x, new_y, new_w, new_h = x, y, w, h

    # [핵심 변경] Two-Step 렌더링: 위치 이동과 크기 조절을 분리하여 OS가 DPI 변경을 인지할 시간을 줍니다.

    # 1단계: 위치(x, y)만 새로운 모니터로 이동시킵니다. (크기 변경 무시)
    move_flags = win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER | win32con.SWP_NOSIZE
    win32gui.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0, move_flags)

    # 2단계: 새로운 모니터 환경에서 인식된 스케일에 맞춰 크기(w, h)를 강제 지정합니다. (위치 이동 무시)
    size_flags = (
        win32con.SWP_NOACTIVATE
        | win32con.SWP_FRAMECHANGED
        | win32con.SWP_NOZORDER
        | win32con.SWP_NOMOVE
    )
    win32gui.SetWindowPos(hwnd, 0, 0, 0, new_w, new_h, size_flags)


# [핵심 로직] 현재 열려 있는 모든 창을 검사하여 조건에 맞는 창 목록을 가져옵니다.
def get_window_list(monitor_info=None):
    windows = []

    # [이해 포인트] EnumWindows API가 각 창을 발견할 때마다 이 콜백(callback) 함수를 반복 실행합니다.
    def callback(hwnd, _):
        if is_valid_window(hwnd):
            # [이해 포인트] 모니터 정보가 있으면 해당 모니터 안에 있는 창만 필터링합니다.
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
        return True  # True를 반환해야 다음 창을 계속 검사합니다.

    win32gui.EnumWindows(callback, None)
    # [이해 포인트] 창의 제목(이름)을 기준으로 알파벳 순으로 정렬합니다.
    windows.sort(key=lambda x: x[1].lower())
    return windows
