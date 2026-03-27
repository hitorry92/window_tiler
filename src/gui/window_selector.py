# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from src.win_utils import get_window_list


class WindowSelector:
    """열려 있는 창 목록을 보여주고 일괄 선택하여 지정하는 다이얼로그 (Cycle 15)"""

    def __init__(self, parent, tracker, callback_ui, callback_status, target_slot=None):
        # [이해 포인트] 다이얼로그 생성 시 필요한 부모 창, 상태 추적기, UI/상태 업데이트 콜백, 대상 슬롯을 인자로 받습니다.
        self.parent = parent
        self.tracker = tracker
        self.callback_ui = callback_ui
        self.callback_status = callback_status
        # [핵심 로직] target_slot이 None이면 일괄 배정 모드, 특정 숫자면 해당 슬롯에만 단일 배정하는 모드로 작동합니다.
        self.target_slot = target_slot  # 단일 슬롯 할당 모드

        # [이해 포인트] Toplevel을 사용하여 메인 윈도우 위에 새로운 팝업 창을 띄웁니다.
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("창 선택")
        self.dialog.geometry("500x600")

        # [안전 장치] transient와 grab_set을 사용하여 이 팝업 창이 열려있는 동안 부모 창을 클릭하지 못하게 막습니다. (모달 창 효과)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 중앙 정렬 (부모 창 기준)
        # [이해 포인트] 부모 창의 위치와 크기를 계산하여 팝업 창이 화면 중앙에 오도록 위치를 조정합니다.
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

        # [이해 포인트] Treeview 위젯을 사용하여 표 형태의 리스트를 생성합니다. selectmode="extended"로 다중 선택이 가능합니다.
        self.tree = ttk.Treeview(
            list_card, columns=("title"), show="headings", selectmode="extended"
        )
        self.tree.heading("title", text="열려 있는 창 제목")
        self.tree.column("title", width=400)

        # [이해 포인트] 창 목록이 길어질 경우를 대비해 수직 스크롤바를 연결합니다.
        sc = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")

        # 더블클릭으로 적용
        # [이해 포인트] 리스트 항목을 더블클릭하면 창을 선택하고 배정하는 _apply 메서드가 바로 실행되도록 이벤트를 바인딩합니다.
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
        # [이해 포인트] 취소 버튼을 누르면 destroy 메서드가 호출되어 다이얼로그 창이 닫힙니다.
        ttk.Button(btn_p, text="취소", command=self.dialog.destroy).pack(
            side="right", padx=5
        )

        self.windows = []
        # [핵심 로직] 창이 처음 열릴 때 현재 열려있는 윈도우 목록을 가져와서 리스트에 채웁니다.
        self._refresh_list()

    def _refresh_list(self):
        # [이해 포인트] 기존 트리에 있던 항목들을 모두 지우고 새 목록을 불러옵니다.
        self.tree.delete(*self.tree.get_children())
        # [핵심 로직] 외부 함수인 get_window_list를 호출하여 현재 활성화된 윈도우 핸들(hwnd)과 제목(title) 목록을 가져옵니다.
        self.windows = get_window_list(None)

        for i, (hwnd, title) in enumerate(self.windows):
            # [안전 장치] 제목이 없거나, 자기 자신(Window Tiler)인 경우 목록에서 제외하여 잘못 선택되는 것을 방지합니다.
            if title and "Window Tiler" not in title:
                # [이해 포인트] tags 매개변수에 인덱스 'i'를 문자열로 저장해두어, 나중에 사용자가 항목을 선택했을 때 어떤 창인지 쉽게 찾을 수 있게 합니다.
                self.tree.insert("", "end", values=(title,), tags=(str(i),))

    def _apply(self):
        # [핵심 로직] 사용자가 Treeview에서 선택한 항목들의 ID 목록을 가져옵니다.
        selected_items = self.tree.selection()
        # [안전 장치] 아무것도 선택하지 않고 적용을 누른 경우, 오류를 방지하기 위해 경고 메시지를 띄우고 함수를 종료합니다.
        if not selected_items:
            messagebox.showinfo("알림", "배치할 창을 하나 이상 선택해 주세요.")
            return

        # [이해 포인트] 선택된 항목의 tag(인덱스)를 사용하여 실제 윈도우 핸들(hwnd)들을 리스트로 모읍니다.
        selected_hwnds = []
        for item in selected_items:
            idx_tag = self.tree.item(item, "tags")[0]
            selected_hwnds.append(self.windows[int(idx_tag)][0])

        # 단일 슬롯 할당 모드
        if self.target_slot is not None:
            # [안전 장치] 단일 슬롯 모드인데 여러 창을 선택한 경우, 사용자에게 알려주고 진행을 막습니다.
            if len(selected_hwnds) > 1:
                messagebox.showinfo("알림", "하나의 창만 선택해 주세요.")
                return
            if selected_hwnds:
                hwnd = selected_hwnds[0]
                # [위험] 이미 다른 슬롯에 같은 창이 배정되어 있을 수 있습니다. 중복 배정을 막기 위해 전체 슬롯을 검사하여 기존 배정을 해제합니다.
                for i, slot in enumerate(self.tracker.slots):
                    if slot["hwnd"] == hwnd:
                        self.tracker.slots[i]["hwnd"] = None

                # [핵심 로직] 지정된 타겟 슬롯에 선택한 창의 핸들을 배정하고, 창 위치를 재조정한 뒤 UI를 업데이트합니다.
                self.tracker.slots[self.target_slot]["hwnd"] = hwnd
                self.tracker.reposition_all()
                self.callback_ui()
                self.callback_status(
                    f"● 슬롯 {self.target_slot}에 창이 배정되었습니다.", "success"
                )
            # [이해 포인트] 작업이 끝나면 다이얼로그를 닫습니다.
            self.dialog.destroy()
            return

        # 일괄 배정 모드
        # [핵심 로직] 현재 비어있는 슬롯들의 인덱스만 모아서 리스트로 만듭니다.
        empty_slots = [i for i, s in enumerate(self.tracker.slots) if s["hwnd"] is None]

        # [안전 장치] 비어있는 슬롯이 하나도 없다면, 더 이상 창을 배정할 수 없으므로 경고를 띄우고 종료합니다.
        if not empty_slots:
            messagebox.showwarning("주의", "배정 가능한 빈 슬롯이 없습니다.")
            self.dialog.destroy()
            return

        count = 0
        # [핵심 로직] 선택한 창들을 비어있는 슬롯 개수만큼 순서대로 하나씩 배정합니다.
        for i, hwnd in enumerate(selected_hwnds):
            if i < len(empty_slots):
                # [위험] 단일 모드와 마찬가지로, 이미 다른 슬롯에 배정된 창이라면 기존 배정을 해제하여 중복을 방지합니다.
                for j, slot in enumerate(self.tracker.slots):
                    if slot["hwnd"] == hwnd:
                        self.tracker.slots[j]["hwnd"] = None
                self.tracker.slots[empty_slots[i]]["hwnd"] = hwnd
                count += 1

        # [이해 포인트] 모든 배정이 끝나면 창들을 정렬하고, UI와 상태바를 업데이트한 후 다이얼로그를 닫습니다.
        self.tracker.reposition_all()
        self.callback_ui()
        self.callback_status(f"● {count}개 창이 슬롯에 배정되었습니다.", "success")
        self.dialog.destroy()
