# -*- coding: utf-8 -*-
# [이해 포인트] tkinter와 관련 모듈을 가져와 GUI 화면을 구성합니다.
import tkinter as tk
from tkinter import ttk, messagebox

# [핵심 로직] 운영체제에 열려 있는 실제 윈도우 창 목록을 가져오는 함수입니다.
from src.win_utils import get_window_list, is_own_window


class ExcludedWindowSelector:
    """자동 지정 시 제외할 창을 선택하는 다이얼로그"""

    def __init__(self, parent, excluded_windows, callback):
        # [이해 포인트] 부모 창, 기존에 제외된 창 목록, 그리고 완료 시 호출할 함수를 저장합니다.
        self.parent = parent
        # [이해 포인트] set(집합) 자료형을 사용하여 중복되는 창 제목을 방지하고 검색 속도를 높입니다.
        self.excluded_windows = set(excluded_windows)  # 이미 제외된 창들
        self.callback = callback  # 선택 완료 후 콜백

        # [핵심 로직] Toplevel을 사용하여 부모 창 위에 새로운 독립된 팝업(다이얼로그) 창을 만듭니다.
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("제외할 창 선택")
        self.dialog.geometry("500x600")

        # [안전 장치] transient와 grab_set을 호출하여 이 팝업 창이 닫히기 전까지 부모 창을 클릭하지 못하게 막습니다 (모달 창).
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # [이해 포인트] 창을 화면 정중앙에 띄우기 위해 부모 창의 위치와 크기를 기준으로 x, y 좌표를 계산합니다.
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

        # [핵심 로직] 엑셀처럼 여러 줄의 데이터를 보여줄 수 있는 Treeview 위젯을 생성합니다.
        self.tree = ttk.Treeview(
            list_card, columns=("title"), show="headings", selectmode="none"
        )
        self.tree.heading("title", text="열려 있는 창 제목")
        self.tree.column("title", width=400)

        # 클릭 시 선택/해제 전환
        # [이해 포인트] 마우스 왼쪽 버튼("<Button-1>")을 클릭했을 때 _on_item_click 함수가 실행되도록 연결합니다.
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
        # [이해 포인트] 창이 처음 열릴 때 현재 열려있는 윈도우 목록을 불러옵니다.
        self._refresh_list()

    def _on_item_click(self, event):
        """항목 클릭 시 선택/해제 전환"""
        # [핵심 로직] 사용자가 클릭한 마우스 좌표(event.x, event.y)를 바탕으로 어떤 항목을 클릭했는지 찾아냅니다.
        item_id = self.tree.identify("item", event.x, event.y)

        # [안전 장치] 빈 공간을 클릭했다면 item_id가 없으므로 오류가 나지 않게 그대로 종료(return)합니다.
        if not item_id:
            return

        # 현재 선택 상태 확인
        # [이해 포인트] 이미 선택된 상태라면 선택을 해제하고, 아니라면 새로 선택하는 '토글(Toggle)' 기능입니다.
        if item_id in self.tree.selection():
            self.tree.selection_remove(item_id)
        else:
            self.tree.selection_add(item_id)

    def _refresh_list(self):
        # [핵심 로직] 이전에 Treeview에 추가되어 있던 모든 항목을 깨끗하게 지웁니다.
        self.tree.delete(*self.tree.get_children())
        # 외부 함수를 호출해 현재 떠 있는 실제 윈도우 창 목록을 다시 가져옵니다.
        self.windows = get_window_list(None)

        for i, (hwnd, title) in enumerate(self.windows):
            # [위험] 이 프로그램 자체의 이름("Window Tiler")이 목록에 포함되는 것을 하드코딩으로 막고 있습니다. 프로그램 이름이 바뀌면 이 부분도 수정해야 합니다.
            if title and not is_own_window(title):
                values = (title,)
                # [이해 포인트] 각 항목이 몇 번째 윈도우인지 기억하기 위해 tags에 인덱스(i)를 문자열로 저장해둡니다.
                tags = (str(i),)
                self.tree.insert("", "end", values=values, tags=tags)

                # 이미 제외된 창은 체크
                # [이해 포인트] 사용자가 이전에 제외하기로 설정했던 창이라면 새로고침 후에도 다시 선택 상태(체크)로 만들어줍니다.
                if title in self.excluded_windows:
                    self.tree.selection_add(self.tree.get_children()[-1])

    def _apply(self):
        # [핵심 로직] Treeview에서 현재 선택되어 있는 모든 항목을 가져옵니다.
        selected_items = self.tree.selection()
        excluded = set()

        for item in selected_items:
            # [이해 포인트] 저장해두었던 태그(tags)에서 인덱스를 꺼내, self.windows 배열에서 정확한 창 정보를 찾습니다.
            idx_tag = self.tree.item(item, "tags")[0]
            hwnd, title = self.windows[int(idx_tag)]
            excluded.add(title)

        # [안전 장치] 최종적으로 선택된 창 제목 목록을 리스트로 변환하여 콜백 함수로 넘겨주고 창을 닫습니다.
        self.callback(list(excluded))
        self.dialog.destroy()
