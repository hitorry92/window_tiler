# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

from .app_config import save_config
from .gui.theme import THEME, setup_styles
from .gui.preview_canvas import PreviewCanvas
from .gui.slot_tree import SlotTreeView
from .gui.window_selector import WindowSelector
from .gui.components.profile_panel import ProfilePanel
from .gui.components.split_panel import SplitPanel, NumericalInputsPanel
from .gui.components.control_panel import ControlPanel


class SettingsGUI:
    # [이해 포인트] SettingsGUI 클래스는 메인 설정 화면을 구성하고 컴포넌트들을 조율하는 역할을 담당합니다.
    def __init__(
        self,
        config,
        profiles,
        tracker,
        start_callback,
        stop_callback,
        update_hotkey_callback=None,
    ):
        # [핵심 로직] 외부에서 주입된 앱 설정(config), 프로필 목록, 트래커(창 제어 객체) 및 제어용 콜백 함수들을 저장합니다.
        self.config = config
        self.profiles = profiles
        self.tracker = tracker
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
        self.root.title("Window Tiler")

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
        ttk.Label(
            laps_frame,
            text="창 배정 기록 (Laps)",
            font=("Segoe UI", 10, "bold"),
            foreground=THEME["text_dim"],
        ).pack(anchor="w", pady=(0, 10))

        self.slot_tree = SlotTreeView(
            laps_frame,
            self.tracker,
            self.update_ui,
            gui_callbacks={"on_right_click": self._on_tree_right_click},
        )

        self.update_ui()

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
            fg="white",
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
        # [이해 포인트] 트리 뷰 목록에서 마우스 우클릭을 했을 때 팝업되는 컨텍스트 메뉴를 띄우는 함수입니다.
        sel = self.slot_tree.tree.selection()
        # [안전 장치] 선택한 아이템이 비어있다면 오류를 피하기 위해 바로 반환(return) 처리합니다.
        if not sel:
            return
        val = self.slot_tree.tree.item(sel[0], "values")
        idx = int(val[0])
        is_locked = False
        overlay_enabled = True

        # [안전 장치] 선택한 인덱스(idx)가 tracker의 슬롯 배열 크기를 넘어가지 않는지(IndexError 방지) 확인합니다.
        if self.tracker and idx < len(self.tracker.slots):
            is_locked = self.tracker.slots[idx].get("locked", False)
            overlay_enabled = self.tracker.slots[idx].get("overlay_enabled", True)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="창 할당...", command=self._assign_window_to_selected_slot
        )
        menu.add_separator()
        menu.add_command(
            label="고정 해제" if is_locked else "고정", command=self._toggle_slot_lock
        )
        menu.add_command(
            label="덮개 끄기" if overlay_enabled else "덮개 켜기",
            command=self._toggle_overlay,
        )
        menu.add_command(label="창 할당 해제", command=self._unbind_selected_slot)

        # [핵심 로직] 마우스를 우클릭한 화면 좌표(event.x_root, event.y_root)에 동적으로 만든 메뉴를 표시합니다.
        menu.post(event.x_root, event.y_root)

    def _assign_window_to_selected_slot(self):
        sel = self.slot_tree.tree.selection()
        if not sel:
            return
        val = self.slot_tree.tree.item(sel[0], "values")
        if not val:
            return
        # [핵심 로직] 트리 뷰에서 선택된 특정 슬롯에 새 윈도우를 배정하기 위해 WindowSelector 대화상자를 오픈합니다.
        WindowSelector(
            self.root, self.tracker, self.update_ui, self.set_status, int(val[0])
        )

    def _toggle_slot_lock(self):
        sel = self.slot_tree.tree.selection()
        if not sel:
            return
        val = self.slot_tree.tree.item(sel[0], "values")
        if not val:
            return
        idx = int(val[0])
        if self.tracker and idx < len(self.tracker.slots):
            # [핵심 로직] 해당 슬롯의 잠금 상태(locked)를 토글(반전)시키고, 결과를 하단 상태 표시줄에 안내합니다.
            self.tracker.toggle_slot_lock(idx)
            locked = self.tracker.slots[idx].get("locked", False)
            self.set_status(
                f"● 슬롯 {idx} 고정됨" if locked else f"● 슬롯 {idx} 고정 해제됨",
                "info",
            )
            self.update_ui()

    def _toggle_overlay(self):
        sel = self.slot_tree.tree.selection()
        if not sel:
            return
        val = self.slot_tree.tree.item(sel[0], "values")
        if not val:
            return
        idx = int(val[0])
        if self.tracker and idx < len(self.tracker.slots):
            # [핵심 로직] 슬롯 덮개(Overlay) 표시를 켜거나 끄고, 그 상태 변화를 사용자에게 텍스트로 알립니다.
            self.tracker.toggle_overlay(idx)
            overlay_enabled = self.tracker.slots[idx].get("overlay_enabled", True)
            self.set_status(
                f"● 슬롯 {idx} 덮개 켜짐"
                if overlay_enabled
                else f"● 슬롯 {idx} 덮개 꺼짐",
                "info",
            )
            self.update_ui()

    def _unbind_selected_slot(self):
        sel = self.slot_tree.tree.selection()
        if not sel:
            return
        val = self.slot_tree.tree.item(sel[0], "values")
        if not val:
            return
        idx = int(val[0])
        if self.tracker and idx < len(self.tracker.slots):
            # [핵심 로직] 선택된 슬롯이 관리하던 창 핸들(hwnd) 정보를 None으로 삭제하여 연결을 끊고 즉시 창들을 재정렬합니다.
            self.tracker.slots[idx]["hwnd"] = None
            self.tracker.reposition_all()
            self.update_ui()
            self.set_status(f"● 슬롯 {idx} 할당 해제됨", "info")
