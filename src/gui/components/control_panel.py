import tkinter as tk
from tkinter import ttk, messagebox
from src.gui.theme import THEME
from src.gui.window_selector import WindowSelector
from src.gui.excluded_window_selector import ExcludedWindowSelector
from src.app_config import save_config


class ControlPanel(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, style="Container.TFrame", **kwargs)
        self.app = app

        btn_start = tk.Button(
            self,
            text="시작",
            bg=THEME["accent"],
            fg="#1a1a2e",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.app.start_callback,
        )
        btn_start.pack(side="left", expand=True, fill="x", padx=5)

        btn_auto = tk.Button(
            self,
            text="자동 지정",
            bg=THEME["warning"],
            fg="#1a1a2e",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=10,
            pady=10,
            cursor="hand2",
            command=self._auto_fill,
        )
        btn_auto.pack(side="left", expand=True, fill="x", padx=5)

        btn_select = tk.Button(
            self,
            text="선택 자동 지정",
            bg=THEME["warning"],
            fg="#1a1a2e",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=10,
            pady=10,
            cursor="hand2",
            command=self._show_window_selector,
        )
        btn_select.pack(side="left", expand=True, fill="x", padx=5)

        btn_exclude = tk.Button(
            self,
            text="예외 선택",
            bg=THEME["text_dim"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=10,
            pady=10,
            cursor="hand2",
            command=self._show_excluded_window_selector,
        )
        btn_exclude.pack(side="left", expand=True, fill="x", padx=5)

        btn_stop = tk.Button(
            self,
            text="중지 (Stop)",
            bg=THEME["error"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.app.stop_callback,
        )
        btn_stop.pack(side="left", expand=True, fill="x", padx=5)

        btn_help = tk.Button(
            self,
            text="도움말",
            bg="#444444",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=10,
            pady=10,
            cursor="hand2",
            command=self._show_help,
        )
        btn_help.pack(side="left", padx=5)

    def _auto_fill(self):
        excluded = self.app.config.get("excluded_windows", [])
        count = self.app.tracker.auto_fill_all_slots(excluded)
        self.app.update_ui()
        self.app.set_status(f"● {count}개 슬롯 자동 할당됨", "success")

    def _show_window_selector(self):
        def on_apply(selected_titles):
            for i, slot in enumerate(self.app.tracker.slots):
                if not slot.get("locked"):
                    slot["hwnd"] = None
            count = self.app.tracker.auto_fill_all_slots(excluded_windows=[])
            self.app.update_ui()
            self.app.set_status(f"● 선택된 {count}개 창 자동 할당됨", "success")

        WindowSelector(
            self.winfo_toplevel(),
            self.app.tracker,
            self.app.update_ui,
            self.app.set_status,
        )

    def _show_excluded_window_selector(self):
        def on_apply(selected_titles):
            self.app.config["excluded_windows"] = selected_titles
            save_config(self.app.config)
            self.app.set_status(
                f"● {len(selected_titles)}개의 예외 창 설정됨", "success"
            )

        excluded = self.app.config.get("excluded_windows", [])
        ExcludedWindowSelector(self.winfo_toplevel(), excluded, on_apply)

    def _show_help(self):
        help_text = (
            "■ Window Tiler 사용 방법 안내 ■\n\n"
            "1. 창 배정 원칙\n"
            "   - 등록되지 않은 창은 타일링되지 않으며, 마우스 조작에 영향을 받지 않습니다.\n"
            "   - [자동 지정]: 현재 켜진 모든 창을 빈 슬롯에 자동 채웁니다.\n"
            "   - [선택 자동 지정]: 원하는 창만 선택하여 채웁니다.\n"
            "   - '창 배정 기록' 우클릭 메뉴에서 특정 슬롯에 직접 할당할 수 있습니다.\n\n"
            "2. 슬롯 관리\n"
            "   - [고정]: 해당 슬롯의 창이 단축키 조작이나 새 창 포커스에 의해 다른 슬롯으로 밀려나지 않습니다.\n"
            "   - [덮개]: 덮개가 켜져 있으면 해당 슬롯의 화면이 약간 어두워지며 클릭 오작동을 방지합니다.\n\n"
            "3. 화면 분할 (미리보기 화면)\n"
            "   - 캔버스 안에서 분할선을 마우스로 드래그하여 비율을 조절할 수 있습니다.\n"
            "   - 우클릭하여 '오른쪽 칸과 합치기', '아래쪽 칸과 합치기' 등을 통해 칸을 합칠 수 있습니다.\n"
            "   - 숫자를 클릭해 직접 비율(0~1)을 입력할 수도 있습니다.\n\n"
            "4. 단축키 조작 (기본 Ctrl+Shift+T)\n"
            "   - 메인 슬롯에 배정된 창과, 단축키 입력 전 포커스 되어 있던 창의 위치가 서로 바뀝니다.\n"
            "   - 고정(Lock)된 슬롯의 창은 스왑되지 않고 무시됩니다."
        )
        messagebox.showinfo("도움말", help_text)
