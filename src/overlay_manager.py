# -*- coding: utf-8 -*-
import tkinter as tk


class OverlayManager:
    """
    비활성 슬롯 위에 투명한 덮개(Overlay)를 생성하여,
    창 내부 클릭/드래그 오작동을 방지하고 슬롯 클릭 이벤트를 가로채는 매니저.
    """

    def __init__(self, root, on_click_callback):
        self.root = root
        self.on_click_callback = on_click_callback
        self.overlays = {}  # slot_index -> tk.Toplevel

    def update_overlays(self, active_slots):
        """
        엔진의 백그라운드 스레드에서 호출되어,
        GUI 메인 스레드 안전하게 오버레이 상태를 동기화하도록 지시합니다.
        active_slots: [(idx, (x, y, w, h)), ...] 형태의 리스트
        """
        self.root.after(0, self._sync, active_slots)

    def _sync(self, active_slots):
        current_indices = [slot[0] for slot in active_slots]

        # 1. 갱신 및 생성
        for idx, rect in active_slots:
            if idx not in self.overlays:
                ov = tk.Toplevel(self.root)
                ov.overrideredirect(True)
                # alpha 0.01: 거의 눈에 보이지 않지만 클릭 이벤트는 캐치함
                ov.attributes("-topmost", True, "-alpha", 0.01)
                ov.configure(bg="black", cursor="hand2")
                # 클릭 시 콜백 실행 (lambda의 기본값 바인딩 트릭 사용)
                ov.bind("<Button-1>", lambda e, i=idx: self._on_click(i))
                self.overlays[idx] = ov
            else:
                ov = self.overlays[idx]

            x, y, w, h = rect
            # 오버레이 창 크기 및 위치 적용
            ov.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
            ov.deiconify()

        # 2. 불필요한 오버레이 제거
        for idx in list(self.overlays.keys()):
            if idx not in current_indices:
                self.overlays[idx].destroy()
                del self.overlays[idx]

    def _on_click(self, idx):
        # 덮개가 클릭되면 타일링 엔진의 교체 콜백 호출
        self.on_click_callback(idx)
