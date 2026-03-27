# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from .theme import THEME


class SlotTreeView:
    # [이해 포인트] UI에서 슬롯 목록을 보여주고 관리하는 트리뷰(표) 컴포넌트입니다.
    def __init__(self, parent, tracker, on_update_callback, gui_callbacks=None):
        self.parent = parent
        self.tracker = tracker
        self.on_update_callback = on_update_callback
        self.gui_callbacks = gui_callbacks or {}
        self.tree = None
        self._drag_source = None
        self.root = None

        self._create_widgets()

    def _create_widgets(self):
        # [이해 포인트] 트리뷰와 스크롤바를 담을 컨테이너 프레임을 생성합니다.
        container = ttk.Frame(self.parent, style="Container.TFrame")
        container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            container,
            columns=("index", "title", "locked", "overlay"),
            show="headings",
            height=15,
        )
        self.tree.heading("index", text="슬롯")
        self.tree.heading("title", text="창 제목")
        self.tree.heading("locked", text="고정")
        self.tree.heading("overlay", text="덮개")
        self.tree.column("index", width=50, anchor="center")
        self.tree.column("title", width=280)
        self.tree.column("locked", width=60, anchor="center")
        self.tree.column("overlay", width=60, anchor="center")

        tree_sc = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sc.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_sc.pack(side="right", fill="y")

        self._bind_events()

    def _bind_events(self):
        # [핵심 로직] 마우스 이벤트(우클릭, 더블클릭, 드래그 앤 드롭)를 트리뷰에 연결(바인딩)합니다.
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_drop)

    def _on_right_click(self, event):
        # [이해 포인트] 마우스 우클릭 시 해당 위치의 행을 식별하고 선택 상태로 만듭니다.
        item = self.tree.identify_row(event.y)
        # [안전 장치] 클릭한 위치에 항목이 없다면 아무 작업도 하지 않고 함수를 종료합니다.
        if not item:
            return
        self.tree.selection_set(item)

        if self.gui_callbacks.get("on_right_click"):
            self.gui_callbacks["on_right_click"](event)

    def _on_double_click(self, event):
        # [안전 장치] 더블클릭한 영역이 실제 데이터가 있는 셀(cell)인지 확인합니다.
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column = self.tree.identify_column(event.x)
        if not column:
            return

        col_idx = int(column.replace("#", ""))
        idx = int(item_id)
        # [위험] 인덱스가 실제 트래커의 슬롯 개수를 초과하지 않도록 검사하여 에러를 방지합니다.
        if idx >= len(self.tracker.slots):
            return

        # [핵심 로직] 클릭한 열(Column) 위치에 따라 다른 동작을 수행합니다.
        if col_idx == 3:
            # 3번째 열(고정): 해당 슬롯의 고정 상태를 켜거나 끕니다.
            self.tracker.toggle_slot_lock(idx)
        elif col_idx == 4:
            # 4번째 열(덮개): 해당 슬롯의 덮개(Overlay) 상태를 켜거나 끕니다.
            self.tracker.toggle_overlay(idx)
        elif col_idx in (1, 2):
            # 1, 2번째 열(슬롯 번호, 창 제목): 해당 슬롯에 연결된 창(hwnd)을 해제(비움)합니다.
            self.tracker.slots[idx]["hwnd"] = None
            self.tracker.reposition_all()

        # 변경 사항이 있으므로 화면을 업데이트하는 콜백을 호출합니다.
        self.on_update_callback()

    def _on_drag_start(self, event):
        # [핵심 로직] 마우스 왼쪽 버튼을 누를 때 드래그할 원본 항목을 기억합니다.
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self._drag_source = item
        self.tree.selection_set(item)

    def _on_drag_motion(self, event):
        # [이해 포인트] 마우스를 드래그하는 동안 마우스 포인터가 위치한 항목을 시각적으로 선택 상태로 만듭니다.
        if not hasattr(self, "_drag_source") or not self._drag_source:
            return
        target = self.tree.identify_row(event.y)
        if target and target != self._drag_source:
            self.tree.selection_set(target)

    def _on_drag_drop(self, event):
        # [안전 장치] 드래그를 시작한 항목이 없다면 무시합니다.
        if not hasattr(self, "_drag_source") or not self._drag_source:
            return

        # [핵심 로직] 마우스 버튼을 놓은 위치의 대상(target) 항목을 식별하여 두 슬롯의 위치를 바꿉니다(Swap).
        target = self.tree.identify_row(event.y)
        if not target or target == self._drag_source:
            self._drag_source = None
            return

        src_vals = self.tree.item(self._drag_source, "values")
        dst_vals = self.tree.item(target, "values")

        if not src_vals or not dst_vals:
            self._drag_source = None
            return

        src_idx = int(src_vals[0])
        dst_idx = int(dst_vals[0])

        if src_idx < len(self.tracker.slots) and dst_idx < len(self.tracker.slots):
            result = self.tracker.swap_slots(src_idx, dst_idx)
            # [위험] 고정(Locked)된 슬롯이 포함되어 있으면 위치 변경이 거부될 수 있습니다.
            if not result:
                src_locked = self.tracker.slots[src_idx].get("locked", False)
                dst_locked = self.tracker.slots[dst_idx].get("locked", False)
                if src_locked or dst_locked:
                    return "[BLOCKED] Fixed slot"
            self.on_update_callback()

        self._drag_source = None

    def update(self):
        # [이해 포인트] win32gui를 사용해 실제 윈도우 창의 정보를 가져옵니다.
        import win32gui

        # 기존 트리뷰의 모든 항목을 지우고 새로 그립니다.
        self.tree.delete(*self.tree.get_children())

        # [핵심 로직] 트래커가 관리하는 모든 슬롯 정보를 순회하며 트리뷰에 행을 추가합니다.
        for i, slot in enumerate(self.tracker.slots):
            hwnd = slot["hwnd"]
            # [안전 장치] hwnd가 유효한 윈도우 핸들인지(IsWindow) 확인한 뒤에만 창 제목을 가져옵니다.
            title = (
                win32gui.GetWindowText(hwnd)
                if hwnd and win32gui.IsWindow(hwnd)
                else "(비어 있음)"
            )
            # [이해 포인트] 고정 및 덮개 상태를 직관적인 이모지(🔒/☐, 👁/○)로 표현합니다.
            locked_icon = "🔒" if slot.get("locked") else "☐"
            overlay_icon = "👁" if slot.get("overlay_enabled", True) else "○"
            self.tree.insert(
                "", "end", iid=str(i), values=(i, title, locked_icon, overlay_icon)
            )
