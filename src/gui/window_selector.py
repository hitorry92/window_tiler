# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from src.win_utils import get_window_list


class WindowSelector:
    """열려 있는 창 목록을 보여주고 일괄 선택하여 지정하는 다이얼로그 (Cycle 15)"""

    def __init__(self, parent, tracker, callback_ui, callback_status, target_slot=None):
        self.parent = parent
        self.tracker = tracker
        self.callback_ui = callback_ui
        self.callback_status = callback_status
        self.target_slot = target_slot  # 단일 슬롯 할당 모드

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("창 선택")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 중앙 정렬 (부모 창 기준)
        self.dialog.update_idletasks()
        w, h = 500, 600
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        main_p = ttk.Frame(self.dialog, style="Container.TFrame", padding=20)
        main_p.pack(fill="both", expand=True)

        ttk.Label(
            main_p, text="배치할 창들을 선택해 주세요.", style="Container.TLabel"
        ).pack(pady=(0, 5))
        ttk.Label(
            main_p, text="* 다중 선택: Ctrl+클릭 / Shift+클릭", style="Dim.TLabel"
        ).pack(pady=(0, 15))

        # 목록 프레임
        list_card = ttk.Frame(main_p, style="Container.TFrame", padding=2)
        list_card.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            list_card, columns=("title"), show="headings", selectmode="extended"
        )
        self.tree.heading("title", text="열려 있는 창 제목")
        self.tree.column("title", width=400)

        sc = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")

        # 더블클릭으로 적용
        self.tree.bind("<Double-1>", lambda e: self._apply())

        # 하단 버튼
        btn_p = ttk.Frame(main_p, style="Container.TFrame")
        btn_p.pack(fill="x", pady=(20, 0))

        ttk.Button(btn_p, text="선택 창 배정", command=self._apply).pack(
            side="right", padx=5
        )
        ttk.Button(btn_p, text="새로고침", command=self._refresh_list).pack(
            side="right", padx=5
        )
        ttk.Button(btn_p, text="취소", command=self.dialog.destroy).pack(
            side="right", padx=5
        )

        self.windows = []
        self._refresh_list()

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self.windows = get_window_list(None)

        for i, (hwnd, title) in enumerate(self.windows):
            if title and "Window Tiler" not in title:
                self.tree.insert("", "end", values=(title,), tags=(str(i),))

    def _apply(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("알림", "배치할 창을 하나 이상 선택해 주세요.")
            return

        selected_hwnds = []
        for item in selected_items:
            idx_tag = self.tree.item(item, "tags")[0]
            selected_hwnds.append(self.windows[int(idx_tag)][0])

        # 단일 슬롯 할당 모드
        if self.target_slot is not None:
            if len(selected_hwnds) > 1:
                messagebox.showinfo("알림", "하나의 창만 선택해 주세요.")
                return
            if selected_hwnds:
                hwnd = selected_hwnds[0]
                for i, slot in enumerate(self.tracker.slots):
                    if slot["hwnd"] == hwnd:
                        self.tracker.slots[i]["hwnd"] = None
                self.tracker.slots[self.target_slot]["hwnd"] = hwnd
                self.tracker.reposition_all()
                self.callback_ui()
                self.callback_status(
                    f"● 슬롯 {self.target_slot}에 창이 배정되었습니다.", "success"
                )
            self.dialog.destroy()
            return

        # 일괄 배정 모드
        empty_slots = [i for i, s in enumerate(self.tracker.slots) if s["hwnd"] is None]

        if not empty_slots:
            messagebox.showwarning("주의", "배정 가능한 빈 슬롯이 없습니다.")
            self.dialog.destroy()
            return

        count = 0
        for i, hwnd in enumerate(selected_hwnds):
            if i < len(empty_slots):
                for j, slot in enumerate(self.tracker.slots):
                    if slot["hwnd"] == hwnd:
                        self.tracker.slots[j]["hwnd"] = None
                self.tracker.slots[empty_slots[i]]["hwnd"] = hwnd
                count += 1

        self.tracker.reposition_all()
        self.callback_ui()
        self.callback_status(f"● {count}개 창이 슬롯에 배정되었습니다.", "success")
        self.dialog.destroy()
