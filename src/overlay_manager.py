# -*- coding: utf-8 -*-
import tkinter as tk
import win32gui
import win32con


# [이해 포인트] OverlayManager 클래스는 비활성 윈도우(슬롯) 위에 눈에 보이지 않는 투명한 창(오버레이)을 덮어씌웁니다.
# 이를 통해 사용자가 잘못된 곳을 클릭하는 것을 방지하고, 필요한 클릭 이벤트만 가로챌 수 있습니다.
class OverlayManager:
    """
    비활성 슬롯 위에 투명한 덮개(Overlay)를 생성하여,
    창 내부 클릭/드래그 오작동을 방지하고 슬롯 클릭 이벤트를 가로채는 매니저.
    """

    def __init__(self, root, on_click_callback, tracker):
        # [이해 포인트] root: Tkinter 메인 윈도우, on_click_callback: 클릭 시 실행될 함수, tracker: 슬롯들의 상태를 추적하는 객체입니다.
        self.root = root
        self.on_click_callback = on_click_callback
        self.tracker = tracker
        # [핵심 로직] 현재 생성된 오버레이 창들을 저장하는 딕셔너리입니다. (슬롯 번호 -> Toplevel 창 객체)
        self.overlays = {}  # slot_index -> tk.Toplevel

    def update_overlays(self, active_slots_with_hwnd):
        """
        엔진의 백그라운드 스레드에서 호출되어,
        GUI 메인 스레드 안전하게 오버레이 상태를 동기화하도록 지시합니다.
        active_slots_with_hwnd: [(idx, (x, y, w, h), target_hwnd), ...] 형태의 리스트
        """
        # [위험] 백그라운드 스레드에서 직접 GUI(Tkinter)를 수정하면 프로그램이 튕길 수 있습니다!
        # [안전 장치] root.after(0, ...)을 사용하여 메인 GUI 스레드에서 _sync 함수가 안전하게 실행되도록 예약합니다.
        self.root.after(0, self._sync, active_slots_with_hwnd)

    def _sync(self, active_slots_with_hwnd):
        # [이해 포인트] 현재 활성화되어야 하는 슬롯들의 번호만 리스트로 뽑아냅니다.
        current_indices = [slot[0] for slot in active_slots_with_hwnd]

        # 1. 갱신 및 생성
        # [핵심 로직] 활성화된 슬롯마다 오버레이 창이 없다면 새로 만들고, 있다면 위치만 업데이트합니다.
        for idx, rect, target_hwnd in active_slots_with_hwnd:
            if idx not in self.overlays:
                # [핵심 로직] Toplevel은 메인 창과 독립적으로 떠다니는 새 창을 만듭니다.
                ov = tk.Toplevel(self.root)
                # [이해 포인트] overrideredirect(True)는 윈도우의 기본 테두리와 제목 표시줄을 모두 없애줍니다.
                ov.overrideredirect(True)
                # alpha 0.01: 거의 눈에 보이지 않지만 클릭 이벤트는 캐치함
                # [이해 포인트] 투명도를 1%로 설정하여 화면에는 보이지 않지만, 마우스 클릭은 인식하게 만듭니다.
                ov.attributes("-alpha", 0.01)
                ov.configure(bg="black", cursor="hand2")

                # 클릭 시 콜백 실행 (lambda의 기본값 바인딩 트릭 사용)
                # [위험] lambda 안에서 반복문 변수인 idx를 바로 쓰면 나중에 값이 덮어씌워질 수 있으므로 i=idx 처럼 기본값으로 고정해야 합니다.
                ov.bind("<Button-1>", lambda e, i=idx: self._on_click(i))
                self.overlays[idx] = ov

                # 창 소유 관계 설정
                # [안전 장치] win32gui를 통해 오버레이 창이 특정 게임/앱 창에 종속되도록 설정합니다. (창이 항상 그 위에 뜨도록)
                try:
                    overlay_hwnd = int(ov.winfo_id())
                    win32gui.SetWindowLong(
                        overlay_hwnd, win32con.GWL_HWNDPARENT, target_hwnd
                    )
                except Exception as e:
                    print(f"Error setting window owner for overlay {idx}: {e}")
            else:
                ov = self.overlays[idx]

            x, y, w, h = rect
            # 오버레이 창 크기 및 위치 적용
            # [이해 포인트] 타겟 창의 x, y 좌표와 너비(w), 높이(h)에 딱 맞게 오버레이 창을 덮어씌웁니다.
            ov.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            ov.deiconify()

        # 2. 불필요한 오버레이 제거
        # [핵심 로직] 더 이상 필요 없어진(비활성화된) 오버레이 창을 찾아 삭제(destroy)하여 메모리를 정리합니다.
        for idx in list(self.overlays.keys()):
            if idx not in current_indices:
                # [안전 장치] 창이 실제로 아직 존재하는지 확인한 후 삭제해야 에러가 나지 않습니다.
                if self.overlays[idx].winfo_exists():
                    self.overlays[idx].destroy()
                del self.overlays[idx]

    def _on_click(self, idx):
        # [이해 포인트] 사용자가 투명 오버레이를 클릭했을 때 실행되는 함수입니다.
        slot = self.tracker.slots[idx]
        # [안전 장치] 슬롯이 '잠금(locked)' 상태라면 클릭 이벤트를 무시하고 바로 함수를 종료합니다.
        if slot.get("locked", False):
            return
        # 잠겨있지 않다면 처음에 전달받은 클릭 콜백 함수를 실행합니다.
        self.on_click_callback(idx)
