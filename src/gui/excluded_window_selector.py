# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from src.win_utils import get_window_list


class ExcludedWindowSelector:
    """자동 지정 시 제외할 창을 선택하는 다이얼로그"""

    def __init__(self, parent, excluded_windows, callback):
        self.parent = parent
        self.excluded_windows = set(excluded_windows)  # 이미 제외된 창들
        self.callback = callback  # 선택 완료 후 콜백

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("제외할 창 선택")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.update_idletasks()
        w, h = 500, 600
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        main_p = ttk.Frame(self.dialog, style="Container.TFrame", padding=20)
        main_p.pack(fill="both", expand=True)

        ttk.Label(
            main_p,
            text="자동 지정 시 제외할 창을 선택하세요.",
            style="Container.TLabel",
        ).pack(pady=(0, 5))
        ttk.Label(
            main_p,
            text="* 한 번 클릭: 선택 / 선택 취소",
            style="Dim.TLabel",
        ).pack(pady=(0, 15))

        list_card = ttk.Frame(main_p, style="Container.TFrame", padding=2)
        list_card.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            list_card, columns=("title"), show="headings", selectmode="none"
        )
        self.tree.heading("title", text="열려 있는 창 제목")
        self.tree.column("title", width=400)

        # 클릭 시 선택/해제 전환
        self.tree.bind("<Button-1>", self._on_item_click)

        sc = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")

        btn_p = ttk.Frame(main_p, style="Container.TFrame")
        btn_p.pack(fill="x", pady=(20, 0))

        ttk.Button(btn_p, text="적용", command=self._apply).pack(side="right", padx=5)
        ttk.Button(btn_p, text="새로고침", command=self._refresh_list).pack(
            side="right", padx=5
        )
        ttk.Button(btn_p, text="취소", command=self.dialog.destroy).pack(
            side="right", padx=5
        )

        self.windows = []
        self._refresh_list()

    def _on_item_click(self, event):
        """항목 클릭 시 선택/해제 전환"""
        item_id = self.tree.identify("item", event.x, event.y)
        if not item_id:
            return

        # 현재 선택 상태 확인
        if item_id in self.tree.selection():
            self.tree.selection_remove(item_id)
        else:
            self.tree.selection_add(item_id)

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self.windows = get_window_list(None)

        for i, (hwnd, title) in enumerate(self.windows):
            if title and "Window Tiler" not in title:
                values = (title,)
                tags = (str(i),)
                self.tree.insert("", "end", values=values, tags=tags)

                # 이미 제외된 창은 체크
                if title in self.excluded_windows:
                    self.tree.selection_add(self.tree.get_children()[-1])

    def _apply(self):
        selected_items = self.tree.selection()
        excluded = set()

        for item in selected_items:
            idx_tag = self.tree.item(item, "tags")[0]
            hwnd, title = self.windows[int(idx_tag)]
            excluded.add(title)

        self.callback(list(excluded))
        self.dialog.destroy()
