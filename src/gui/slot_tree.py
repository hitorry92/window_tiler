# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from .theme import THEME


class SlotTreeView:
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
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_drop)

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

    def _on_double_click(self, event):
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
        if col_idx not in (3, 4):
            return

        idx = int(item_id)
        if idx >= len(self.tracker.slots):
            return

        if col_idx == 3:
            self.tracker.toggle_slot_lock(idx)
        elif col_idx == 4:
            self.tracker.toggle_overlay(idx)

        self.on_update_callback()

    def _on_drag_start(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self._drag_source = item
        self.tree.selection_set(item)

    def _on_drag_motion(self, event):
        if not hasattr(self, "_drag_source") or not self._drag_source:
            return
        target = self.tree.identify_row(event.y)
        if target and target != self._drag_source:
            self.tree.selection_set(target)

    def _on_drag_drop(self, event):
        if not hasattr(self, "_drag_source") or not self._drag_source:
            return

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
            if not result:
                src_locked = self.tracker.slots[src_idx].get("locked", False)
                dst_locked = self.tracker.slots[dst_idx].get("locked", False)
                if src_locked or dst_locked:
                    return "[BLOCKED] Fixed slot"
            self.on_update_callback()

        self._drag_source = None

    def update(self):
        import win32gui

        self.tree.delete(*self.tree.get_children())

        for i, slot in enumerate(self.tracker.slots):
            hwnd = slot["hwnd"]
            title = (
                win32gui.GetWindowText(hwnd)
                if hwnd and win32gui.IsWindow(hwnd)
                else "(비어 있음)"
            )
            locked_icon = "🔒" if slot.get("locked") else "☐"
            overlay_icon = "👁" if slot.get("overlay_enabled", True) else "○"
            self.tree.insert(
                "", "end", iid=str(i), values=(i, title, locked_icon, overlay_icon)
            )
