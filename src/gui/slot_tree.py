# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from .theme import THEME
from ..app_config import DEFAULT_SWAP_MODE, get_config_value


class SlotTreeView:
    # [이해 포인트] UI에서 슬롯 목록을 보여주고 관리하는 트리뷰(표) 컴포넌트입니다.
    def __init__(
        self,
        parent,
        tracker,
        trackers,
        app_config,
        on_update_callback,
        gui_callbacks=None,
    ):
        self.parent = parent
        self.tracker = tracker
        self.trackers = trackers
        self.config = app_config
        self.on_update_callback = on_update_callback
        self.gui_callbacks = gui_callbacks or {}
        self.tree = None
        self._drag_source = None
        self.root = None

        # [글로벌 모드] 트래커 간 매핑 정보를 저장하는 리스트 (iid -> (mon_idx, slot_idx))
        self.slot_mapping = []

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
        self.tree.column("index", width=100, anchor="center")
        self.tree.column("title", width=250)
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

    def _get_target_tracker_and_slot(self, iid):
        # iid(문자열 인덱스)를 받아서 실제 모니터 인덱스와 슬롯 인덱스, 트래커를 반환합니다.
        try:
            idx = int(iid)
            if idx < len(self.slot_mapping):
                mon_idx, slot_idx = self.slot_mapping[idx]
                target_tracker = self.trackers.get(mon_idx)
                return target_tracker, slot_idx
        except ValueError:
            pass
        return None, -1

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

        target_tracker, target_slot_idx = self._get_target_tracker_and_slot(item_id)
        if not target_tracker or target_slot_idx == -1:
            return

        # [핵심 로직] 클릭한 열(Column) 위치에 따라 다른 동작을 수행합니다.
        if col_idx == 3:
            # 3번째 열(고정): 해당 슬롯의 고정 상태를 켜거나 끕니다.
            target_tracker.toggle_slot_lock(target_slot_idx)
        elif col_idx == 4:
            # 4번째 열(덮개): 해당 슬롯의 덮개(Overlay) 상태를 켜거나 끕니다.
            target_tracker.toggle_overlay(target_slot_idx)
        elif col_idx in (1, 2):
            # 1, 2번째 열(슬롯 번호, 창 제목): 해당 슬롯에 연결된 창(hwnd)을 해제(비움)합니다.
            target_tracker.slots[target_slot_idx]["hwnd"] = None
            target_tracker.reposition_all()

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

        src_tracker, src_slot_idx = self._get_target_tracker_and_slot(self._drag_source)
        dst_tracker, dst_slot_idx = self._get_target_tracker_and_slot(target)

        if not src_tracker or not dst_tracker:
            self._drag_source = None
            return

        # 로컬 스왑인 경우 (같은 모니터 안에서 드래그)
        if src_tracker == dst_tracker:
            result = src_tracker.swap_slots(src_slot_idx, dst_slot_idx)
            if not result:
                src_locked = src_tracker.slots[src_slot_idx].get("locked", False)
                dst_locked = src_tracker.slots[dst_slot_idx].get("locked", False)
                if src_locked or dst_locked:
                    self._drag_source = None
                    return "[BLOCKED] Fixed slot"
            self.on_update_callback()

        # 글로벌 스왑인 경우 (다른 모니터로 드래그)
        else:
            with src_tracker.lock, dst_tracker.lock:
                slot_src = src_tracker.slots[src_slot_idx]
                slot_dst = dst_tracker.slots[dst_slot_idx]

                if slot_src.get("locked") or slot_dst.get("locked"):
                    self._drag_source = None
                    return "[BLOCKED] Fixed slot"

                # 스왑 처리
                src_tracker.slots[src_slot_idx], dst_tracker.slots[dst_slot_idx] = (
                    slot_dst,
                    slot_src,
                )

            src_tracker.reposition_all()
            dst_tracker.reposition_all()
            self.on_update_callback()

        self._drag_source = None

    def update(self):
        # [이해 포인트] win32gui를 사용해 실제 윈도우 창의 정보를 가져옵니다.
        import win32gui

        # 기존 트리뷰의 모든 항목을 지우고 새로 그립니다.
        self.tree.delete(*self.tree.get_children())
        self.slot_mapping = []

        is_global_mode = (
            get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE) == "global"
        )

        # [글로벌 모드] 모든 트래커의 슬롯을 통합해서 보여줍니다.
        if is_global_mode and self.trackers:
            global_index = 0
            # 모니터 번호 순서대로 정렬하여 출력
            for mon_idx in sorted(self.trackers.keys()):
                tracker = self.trackers[mon_idx]
                for i, slot in enumerate(tracker.slots):
                    hwnd = slot["hwnd"]
                    title = (
                        win32gui.GetWindowText(hwnd)
                        if hwnd and win32gui.IsWindow(hwnd)
                        else "(비어 있음)"
                    )
                    locked_icon = "🔒" if slot.get("locked") else "☐"
                    overlay_icon = "👁" if slot.get("overlay_enabled", True) else "○"

                    # [M0] 0번 형태의 직관적인 라벨 생성
                    display_index = f"[M{mon_idx}] {i}번"

                    self.tree.insert(
                        "",
                        "end",
                        iid=str(global_index),
                        values=(display_index, title, locked_icon, overlay_icon),
                    )
                    # 매핑 정보 저장
                    self.slot_mapping.append((mon_idx, i))
                    global_index += 1

        # [로컬 모드] 기존처럼 현재 선택된 모니터의 슬롯만 보여줍니다.
        else:
            if not self.tracker:
                return

            for i, slot in enumerate(self.tracker.slots):
                hwnd = slot["hwnd"]
                title = (
                    win32gui.GetWindowText(hwnd)
                    if hwnd and win32gui.IsWindow(hwnd)
                    else "(비어 있음)"
                )
                locked_icon = "🔒" if slot.get("locked") else "☐"
                overlay_icon = "👁" if slot.get("overlay_enabled", True) else "○"

                # [수정] 모니터 인덱스를 명시 (단일 모드에서도 표기 방식 적용)
                mon_idx = self.tracker.monitor_index
                display_index = f"[M{mon_idx}] {i}번"

                self.tree.insert(
                    "",
                    "end",
                    iid=str(i),
                    values=(display_index, title, locked_icon, overlay_icon),
                )
                # 매핑 정보 저장 (현재 모니터 전용)
                self.slot_mapping.append((mon_idx, i))
