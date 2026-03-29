# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

from .app_config import save_config, APP_NAME
from .gui.theme import THEME, setup_styles
from .gui.preview_canvas import PreviewCanvas
from .gui.slot_tree import SlotTreeView
from .gui.window_selector import WindowSelector
from .gui.components.profile_panel import ProfilePanel
from .gui.components.split_panel import SplitPanel, NumericalInputsPanel
from .gui.components.control_panel import ControlPanel


class SettingsGUI:
    def __init__(
        self,
        app_instance,
        config,
        profiles,
        trackers,
        start_callback,
        stop_callback,
        update_hotkey_callback=None,
    ):
        self.app_instance = app_instance
        self.config = config
        self.profiles = profiles
        self.trackers = trackers
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.update_hotkey_callback = update_hotkey_callback

        self.profile_modified = False

        # [이해 포인트] 초기화 단계에서는 UI 컴포넌트들을 None으로 선언해 두고, 실제로 화면이 표시될 때(show) 객체들을 생성합니다.
        self.root = None
        self.preview_canvas = None
        self.profile_panel = None
        self.split_panel = None
        self.numerical_inputs_panel = None
        self.control_panel = None
        self.slot_tree = None

    @property
    def tracker(self):
        # [핵심 로직] 현재 설정된 monitor_index에 해당하는 트래커를 동적으로 반환합니다.
        idx = self.config.get("monitor_index", 0)
        return self.trackers.get(idx)

    def show(self):
        # [안전 장치] 창이 이미 화면에 존재하고 파괴되지 않았는지(winfo_exists) 확인하여 중복 생성을 방지합니다.
        if self.root and self.root.winfo_exists():
            self.root.deiconify()  # [핵심 로직] 숨겨져 있던 창을 다시 사용자 화면에 표시합니다.
        else:
            self._create_ui()  # 창이 존재하지 않으면 새롭게 UI를 구성합니다.
        self.update_ui()

    def _create_ui(self):
        # [안전 장치] 혹시라도 메서드가 중복 호출되었을 때 창이 이미 있으면 초기화 과정을 건너뜁니다.
        if self.root and self.root.winfo_exists():
            return

        # [핵심 로직] Tkinter의 최상위 메인 윈도우(root) 객체를 생성하고 제목을 설정합니다.
        self.root = tk.Tk()
        self.root.title(APP_NAME)

        # [위험] 창 우상단의 X 버튼(닫기)을 눌렀을 때 프로그램이 바로 종료되는 것을 막고 커스텀 함수(hide)를 실행합니다.
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.style = setup_styles(self.root)

        bg_frame = ttk.Frame(self.root, style="Bg.TFrame", padding=40)
        bg_frame.pack(fill="both", expand=True)

        container = ttk.Frame(bg_frame, style="Container.TFrame", padding=30)
        container.pack(fill="both", expand=True)

        # [이해 포인트] 사용자가 창을 최소화하는 등의 동작으로 창이 가려질 때('<Unmap>')의 이벤트를 바인딩하여 처리합니다.
        self.root.bind("<Unmap>", self._on_unmap)

        # 1. Title
        ttk.Label(container, text="WINDOW TILER", style="Header.TLabel").pack(
            pady=(0, 20)
        )

        # 2. Profile / Monitor Selector (Top)
        # [이해 포인트] 각 패널을 생성할 때 자기 자신(app=self)을 넘겨주어 패널에서 메인 GUI의 변수나 함수에 접근하게 합니다.
        self.profile_panel = ProfilePanel(container, app=self)
        self.profile_panel.pack(fill="x", pady=(0, 15))

        # Main Panes
        main_pane = ttk.Frame(container, style="Container.TFrame")
        main_pane.pack(fill="both", expand=True, pady=(0, 10))

        left_pane = ttk.Frame(main_pane, style="Container.TFrame")
        left_pane.pack(side="left", fill="y", padx=(0, 30))

        right_pane = ttk.Frame(main_pane, style="Container.TFrame")
        right_pane.pack(side="left", fill="both", expand=True)

        # 3. Canvas Layout Preview (Left Top)
        tk.Label(
            left_pane,
            text="🎨 미리보기 (분할)",
            font=("Segoe UI", 10, "bold"),
            fg=THEME["text"],
            bg=THEME["surface"],
        ).pack(anchor="w", pady=(0, 5))

        self.preview_canvas = PreviewCanvas(
            left_pane,
            tracker=self.tracker,
            config=self.config,
            profiles=self.profiles,
            on_layout_update=self.request_layout_update,
            on_profile_modified=self.mark_profile_modified,
            on_save_config=self.save_config,
            on_status_update=self.set_status,
            on_show_window_selector=self._show_window_selector_wrapper,
            width=540,
            height=300,
        )
        self.preview_canvas.pack(pady=(0, 10))

        # 4. Split Editor Panel
        self.split_panel = SplitPanel(left_pane, app=self)
        self.split_panel.pack(fill="x", pady=(0, 10))

        self.numerical_inputs_panel = NumericalInputsPanel(left_pane, app=self)
        self.numerical_inputs_panel.pack(fill="x", pady=(0, 25))

        # 5. Controls Panel
        self.control_panel = ControlPanel(left_pane, app=self)
        self.control_panel.pack(fill="x")

        # 6. Slot Tree (Right)
        laps_frame = ttk.Frame(right_pane, style="Container.TFrame")
        laps_frame.pack(fill="both", expand=True)
        tk.Label(
            laps_frame,
            text="📋 창 배정 기록",
            font=("Segoe UI", 10, "bold"),
            fg=THEME["text"],
            bg=THEME["surface"],
        ).pack(anchor="w", pady=(0, 10))

        self.slot_tree = SlotTreeView(
            laps_frame,
            self.tracker,
            self.trackers,
            self.config,
            self.update_ui,
            gui_callbacks={"on_right_click": self._on_tree_right_click},
        )

        self.update_ui()

    def global_auto_fill(self, excluded_windows=None, is_specific_targets=False):
        if self.app_instance:
            return self.app_instance.global_auto_fill(
                excluded_windows, is_specific_targets
            )
        return 0

    def set_status(self, text, status_type="info"):
        # [안전 장치] profile_panel 객체가 존재하는지 검사한 후 상태 메세지를 전달하여 프로그램 크래시를 막습니다.
        if self.profile_panel:
            self.profile_panel.set_status(text, status_type)

    def mark_profile_modified(self):
        # [이해 포인트] 프로필에 변경사항이 발생했음을 플래그(profile_modified)로 기록하고 관련 콤보박스 UI를 갱신합니다.
        self.profile_modified = True
        if self.profile_panel:
            self.profile_panel.update_profile_combo_display()

    def save_config(self):
        # [핵심 로직] 현재 변경된 환경설정 내용(config)을 디스크 파일에 영구적으로 저장합니다.
        save_config(self.config)

    def request_layout_update(self, reposition=False):
        # [핵심 로직] 트래커에 전체 창 레이아웃 갱신을 요청하고, reposition이 참이면 화면상에 창들을 다시 정렬시킵니다.
        if self.tracker:
            self.tracker.update_layout()
            if reposition:
                self.tracker.reposition_all()
        self.update_ui()
        self.mark_profile_modified()

    def update_ui(self):
        # [안전 장치] 캔버스가 초기화되기 전에 이 함수가 호출되는 것을 방지합니다.
        if not self.preview_canvas:
            return

        # [핵심 로직] 최신 상태의 트래커, 설정, 프로필 데이터를 각 UI 컴포넌트에 주입하고 다시 그리게 만듭니다.
        self.preview_canvas.tracker = self.tracker
        self.preview_canvas.config = self.config
        self.preview_canvas.profiles = self.profiles
        self.preview_canvas.update_drawing()

        if self.numerical_inputs_panel:
            self.numerical_inputs_panel.update_inputs()
        if self.slot_tree:
            self.slot_tree.tracker = self.tracker
            self.slot_tree.update()

    def _show_window_selector_wrapper(self, target_idx):
        # [이해 포인트] 다른 UI에서 호출하기 쉽게, 윈도우 선택기를 생성해주는 래퍼(Wrapper) 함수입니다.
        WindowSelector(
            self.root, self.tracker, self.update_ui, self.set_status, target_idx
        )

    def _show_monitor_overlay(self, index, monitor):
        # [이해 포인트] 모니터를 식별하기 쉽게 화면 한가운데에 투명하고 큰 숫자 라벨을 임시 띄우는 창(Overlay)을 생성합니다.
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)  # 운영체제 창 테두리 및 타이틀바를 숨깁니다.
        overlay.attributes(
            "-topmost", True, "-alpha", 0.8
        )  # 항상 최상단 및 투명도를 설정합니다.

        lbl = tk.Label(
            overlay,
            text=f" MONITOR {index} ",
            fg=THEME["text"],
            bg=THEME["accent"],
            font=("Segoe UI", 24, "bold"),
            padx=30,
            pady=15,
            relief="flat",
        )
        lbl.pack()

        overlay.update_idletasks()
        w, h = lbl.winfo_reqwidth(), lbl.winfo_reqheight()

        # [핵심 로직] 모니터의 X, Y 좌표 및 너비, 높이 중앙 값을 계산하여 오버레이 창 위치를 잡아줍니다.
        mx = monitor["x"] + (monitor["width"] - w) // 2
        my = monitor["y"] + (monitor["height"] - h) // 2
        overlay.geometry(f"{w}x{h}+{mx}+{my}")

        # [안전 장치] 타이머를 설정해 1200ms(1.2초)가 지나면 오버레이 창이 자동으로 삭제(destroy)되도록 합니다.
        self.root.after(1200, overlay.destroy)

    def _on_unmap(self, event):
        # [위험] 창이 단순히 숨겨지는 상황을 감지하여 윈도우 작업을 취소(withdraw)하고 트레이 모드 전환 등에 대응합니다.
        if event.widget == self.root and self.root.state() == "iconified":
            self.root.withdraw()

    def hide(self):
        # [위험] 메인 윈도우를 닫으려 할 때 완전 종료할 것인지, 트레이에서 백그라운드로 남겨둘 것인지 선택지를 제공합니다.
        if self.root:
            choice = messagebox.askyesnocancel(
                "창 닫기",
                "트레이로 이동하시겠습니까?\n\n"
                "예: 트레이에서 백그라운드로 계속 실행\n"
                "아니오: 프로그램 완전히 종료",
            )
            if choice is True:
                self.root.withdraw()  # [핵심 로직] 창을 숨기고 백그라운드로 전환합니다.
            elif choice is False:
                self.quit()  # [핵심 로직] 프로그램 완전 종료 루틴을 호출합니다.

    def quit(self):
        # [위험] Tkinter의 메인루프를 중단(quit)하고 관련된 모든 창과 위젯 메모리를 해제(destroy)합니다.
        if self.root:
            self.root.quit()
            self.root.destroy()

    def loop(self):
        # [이해 포인트] 이 함수는 계속해서 자신을 재귀 호출(after)하여 앱의 지속적인 백그라운드 체크나 로직을 담당할 수 있는 타이머 기반 루프입니다.
        def check_assignment_mode():
            if not self.root:
                return
            self.root.after(500, check_assignment_mode)

        # [핵심 로직] 0.5초(500ms) 뒤 check_assignment_mode 함수를 처음 시작하고, 화면의 메인 이벤트 처리 루프(mainloop)를 실행합니다.
        self.root.after(500, check_assignment_mode)
        self.root.mainloop()

    # --- Tree View Context Menu Methods ---
    def _on_tree_right_click(self, event):
        from .core.slot_tree_controller import SlotTreeController

        if not hasattr(self, "tree_controller"):
            self.tree_controller = SlotTreeController(self)
        self.tree_controller.handle_right_click(event, self.slot_tree)
