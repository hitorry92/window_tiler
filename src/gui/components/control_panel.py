import tkinter as tk
from tkinter import ttk, messagebox
from src.gui.theme import THEME
from src.gui.window_selector import WindowSelector
from src.gui.excluded_window_selector import ExcludedWindowSelector
from src.app_config import save_config


class ControlPanel(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, style="Container.TFrame", **kwargs)
        self.app = app  # app is SettingsGUI instance
        # self.app_instance를 직접 참조하는 대신, app을 통해 호출하도록 구조 변경

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
            text="예외 지정",
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
        swap_mode = self.app.config.get("swap_mode", "local")

        if swap_mode == "global":
            # SettingsGUI에 프록시(대리) 함수를 만들어 호출
            count = self.app.global_auto_fill(excluded)
        else:
            # 기존 로컬(모니터별) 지정
            count = self.app.tracker.auto_fill_all_slots(excluded)

        self.app.update_ui()
        self.app.set_status(f"● {count}개 슬롯 자동 할당됨", "success")

    def _show_window_selector(self):
        def on_apply(selected_hwnds):
            swap_mode = self.app.config.get("swap_mode", "local")
            if swap_mode == "global":
                count = self.app.global_auto_fill(
                    selected_hwnds, is_specific_targets=True
                )
                self.app.update_ui()
                self.app.set_status(f"● 선택된 {count}개 창 글로벌 할당됨", "success")
            else:
                # 로컬 모드일 때의 선택 지정 로직
                count = 0
                for slot in self.app.tracker.slots:
                    if not slot.get("locked"):
                        slot["hwnd"] = None

                for i, slot in enumerate(self.app.tracker.slots):
                    if count < len(selected_hwnds) and not slot.get("locked"):
                        slot["hwnd"] = selected_hwnds[count]
                        count += 1

                self.app.tracker.reposition_all()
                self.app.update_ui()
                self.app.set_status(f"● 선택된 {count}개 창 로컬 할당됨", "success")

        WindowSelector(
            self.winfo_toplevel(),
            self.app.tracker,
            self.app.update_ui,
            self.app.set_status,
            on_apply_callback=on_apply,
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
        help_text = """■ Window Tiler: 완벽 가이드 ■
──────────────────
[1] 핵심 개념
──────────────────
• 메인 슬롯 (Main Slot):
  - 현재 집중적으로 작업할 핵심 창을 배치하는 공간입니다.
  - 이 공간의 위치는 '🎨 미리보기 (분할)'에서 칸을 클릭(좌클릭 또는 우클릭 메뉴)하여 지정할 수 있습니다.
• 사이드 슬롯 (Side Slots):
  - 메인 슬롯 외의 다른 창들을 배치하는 공간입니다.
  - 타일링이 시작되면, 모든 사이드 슬롯 위에는 '투명 덮개(Overlay)'가 씌워져 창 내부의 실수 클릭을 막고, 클릭 시 '창 위치 교환'만 일어나도록 보장합니다.
  - 사이드 슬롯의 창을 작업하기 위해 클릭하면, 해당 창이 메인 슬롯으로 이동하여 집중 작업할 수 있도록 자리가 교체됩니다.
• 로컬 모드 vs. 글로벌 모드:
  - 로컬 모드: 각 모니터가 자신만의 '메인 슬롯'을 가지고 독립적으로 작동합니다.
  - 글로벌 모드: 모든 모니터가 단 하나의 '글로벌 메인 슬롯'을 공유하며 하나의 작업 공간처럼 연동됩니다.
──────────────────
[2] 설정 창: 상단 패널
──────────────────
• 👤 프로필: 현재의 복잡한 화면 분할 상태를 이름으로 저장하고 언제든 다시 불러올 수 있습니다.
• 💻 모니터 선택: 화면 분할(레이아웃)을 편집할 모니터를 선택합니다. 이 선택은 '좌측 패널'의 편집 대상에만 영향을 주며, 타일링 작동 방식 자체와는 무관합니다.
• 🔄 모드 전환: '로컬 모드'와 '글로벌 모드'를 전환합니다.
──────────────────
[3] 설정 창: 좌측 패널 (레이아웃 편집)
──────────────────
• 🎨 미리보기 (분할):
  - 드래그: 분할선을 마우스로 끌어서 비율을 직관적으로 조절합니다.
  - 클릭/우클릭: 칸을 선택하여 '메인 슬롯으로 지정'하거나 '칸 합치기/나누기' 등 고급 편집이 가능합니다.
• 분할 편집:
  - 수동/자동/수치 조정: 분할선을 직접 추가/삭제하거나, 가로/세로 개수를 입력해 자동 균등 분할하거나, 생성된 분할선의 비율 값을 숫자로 정밀하게 조정할 수 있습니다.
  - ⟷ 간격(Gap): 창과 창 사이의 여백(픽셀)을 설정하여 시각적 편안함을 더합니다.
• 제어 버튼:
  - [시작/중지]: 타일링 기능을 켜거나 끕니다.
  - [자동 지정]: 현재 열린 창들을 모든 슬롯에 자동으로 배치합니다.
  - [선택 자동 지정]: 목록에서 원하는 창만 골라서 자동 배치합니다.
  - [예외 지정]: 자동 지정 시 포함되지 않을 창을 영구적으로 제외시킵니다. (e.g., 메신저)
• 🔢 단축키: 단축키를 설정합니다. (기본: Ctrl+Shift+E)
──────────────────
[4] 설정 창: 우측 패널 (창 배정 기록)
──────────────────
• 📋 창 배정 기록:
  - 로컬 모드: 현재 '🖥️ 모니터 선택'에서 선택된 모니터의 창 목록만 독립적으로 표시됩니다.
  - 글로벌 모드: 모든 모니터의 창 목록이 이곳에 통합되어 표시됩니다.
• 창 교환 (드래그 앤 드롭): 목록에서 창을 드래그하여 다른 슬롯(다른 모니터 포함)으로 옮겨 자리를 바꿀 수 있습니다.
• 고급 제어 (더블클릭/우클릭):
  - [고정]: 특정 창(e.g., 동영상, 실시간 로그)을 한 자리에 계속 두어야 할 때 사용합니다. '고정'된 창은 어떤 스왑 동작에도 자리를 바꾸지 않습니다.
  - [덮개 끄기]: '고정'된 창을 스왑은 막되 그 안에서 스크롤이나 클릭 등 직접 조작이 필요할 때 사용합니다. '덮개'를 끈 고정 창은 완벽한 독립 작업 공간이 됩니다.
──────────────────
[5] 창 위치 교환 (Swap) 방법
──────────────────
사이드 창과 메인 창의 위치를 바꾸는 3가지 방법이 있습니다.
• 방법 1 (창 활성화): 사이드 창을 마우스로 직접 클릭하거나 Alt+Tab으로 선택 시, 자동으로 메인 창과 자리가 교체됩니다.
• 방법 2 (투명 덮개 클릭): 사이드 창 위를 클릭하면(실제로는 투명 덮개가 클릭됨), 메인 창과 자리가 교체됩니다.
• 방법 3 (UI에서 드래그): '📋 창 배정 기록' 목록에서 원하는 창을 드래그하여 다른 창 위치에 놓으면 서로 교체됩니다.
──────────────────
[6] 스마트 단축키 (기본: Ctrl+Shift+E)
──────────────────
• 글로벌 모드: 모든 모니터의 타일링을 한 번에 켜거나 끄는 '마스터 키'로 작동합니다.
• 로컬 모드: 현재 '활성화된 창'이 있는 모니터의 타일링만 켜거나 끄는 '스마트 키'로 작동합니다."""

        top = tk.Toplevel(self.winfo_toplevel())
        top.title("도움말")
        top.geometry("650x550")

        scrollbar = tk.Scrollbar(top)
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(
            top,
            yscrollcommand=scrollbar.set,
            font=("Malgun Gothic", 13),
            wrap="word",
            padx=15,
            pady=15,
            spacing1=5,
            spacing2=3,
            spacing3=5,
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)

        text.insert("1.0", help_text)

        text.tag_add("title", "1.0", "2.0")
        text.tag_config("title", font=("Malgun Gothic", 15, "bold"), spacing1=15)

        text.config(state="disabled")
