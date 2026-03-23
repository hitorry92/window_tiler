# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Listbox, Scrollbar, MULTIPLE
import win32gui
import win32api
import win32con
from .win_utils import get_all_monitors, get_window_list, move_window_precision
from .win_utils import get_window_list
from .app_config import save_config, save_profiles
from .gui.theme import THEME, setup_styles
from .gui.window_selector import WindowSelector


class SettingsGUI:
    def __init__(
        self,
        config,
        profiles,
        tracker,
        start_callback,
        stop_callback,
        update_hotkey_callback=None,
    ):
        self.config = config
        self.profiles = profiles
        self.tracker = tracker
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.update_hotkey_callback = update_hotkey_callback

        self.root = None
        self.preview_canvas = None
        self.v_scroll_frame = None
        self.h_scroll_frame = None
        self.mon_combo = None
        self.prof_combo = None
        self.tree = None
        self.status_label = None
        self.hover_split = None
        self.gap_var = None
        self.btn_interactive = None

        # Drag State
        self.dragging_split = None
        self.hover_split = None

        # UI Styles
        self.style = None

    def show(self):
        if self.root:
            self.root.deiconify()
            return

        self.root = tk.Tk()
        self.root.title("Window Tiler - Stopwatch Edition")
        self.root.configure(bg=THEME["bg"])
        self.root.resizable(False, False)

        self.style = setup_styles(self.root)

        # 전체 화면 배경 (margin 역할)
        bg_frame = ttk.Frame(self.root, style="Bg.TFrame", padding=40)
        bg_frame.pack(fill="both", expand=True)

        # 중앙 컨테이너 (.container 역할 - 둥근 모서리 느낌을 위해 테두리/패딩 부여)
        container = ttk.Frame(bg_frame, style="Container.TFrame", padding=30)
        container.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Unmap>", self._on_unmap)

        # 1. Title (H1)
        title_lbl = ttk.Label(container, text="WINDOW TILER", style="Header.TLabel")
        title_lbl.pack(pady=(0, 20))

        # 설정 영역 (콤보박스)
        cfg_frame = ttk.Frame(container, style="Container.TFrame")
        cfg_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(cfg_frame, text="모니터:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        self.mon_combo = ttk.Combobox(cfg_frame, state="readonly", width=15)
        self.mon_combo.pack(side="left", padx=(0, 15))

        ttk.Label(cfg_frame, text="프로필:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        self.prof_combo = ttk.Combobox(cfg_frame, state="readonly", width=12)
        self.prof_combo.pack(side="left", padx=(0, 5))
        ttk.Button(cfg_frame, text="+", width=2, command=self._add_profile).pack(
            side="left", padx=1
        )
        ttk.Button(cfg_frame, text="삭제", width=4, command=self._delete_profile).pack(
            side="left", padx=1
        )

        self.status_label = tk.Label(
            cfg_frame,
            text="○ 대기 중",
            fg=THEME["text_dim"],
            bg=THEME["surface"],
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="right")

        # 메인 2단 구조 컨테이너
        main_pane = ttk.Frame(container, style="Container.TFrame")
        main_pane.pack(fill="both", expand=True, pady=(0, 10))

        # 좌측 패널 (미리보기 + 분할설정 + 컨트롤)
        left_pane = ttk.Frame(main_pane, style="Container.TFrame")
        left_pane.pack(side="left", fill="y", padx=(0, 30))

        # 우측 패널 (창 배정 기록)
        right_pane = ttk.Frame(main_pane, style="Container.TFrame")
        right_pane.pack(side="left", fill="both", expand=True)

        # 2. Canvas Layout Preview (좌측 최상단)
        self.preview_canvas = tk.Canvas(
            left_pane,
            width=540,
            height=300,
            bg="#0a0a0e",
            highlightthickness=2,
            highlightbackground=THEME["accent"],
            cursor="arrow",
        )
        self.preview_canvas.pack(pady=(0, 10))
        self.preview_canvas.bind("<Button-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self.preview_canvas.bind("<Button-3>", self._on_canvas_right_click)

        split_btn_p = ttk.Frame(left_pane, style="Container.TFrame")
        split_btn_p.pack(fill="x", pady=(0, 10))

        # 간격
        ttk.Label(split_btn_p, text="간격:", style="Container.TLabel").pack(side="left")
        self.gap_var = tk.StringVar(value=str(self.config.get("gap", 0)))
        gap_e = ttk.Entry(split_btn_p, textvariable=self.gap_var, width=5)
        gap_e.pack(side="left", padx=5)
        gap_e.bind("<Return>", lambda e: self._on_gap_change())

        # 핫키
        ttk.Label(split_btn_p, text="단축키:", style="Container.TLabel").pack(
            side="left", padx=(10, 0)
        )
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", "Ctrl+Shift+T"))
        self.hotkey_entry = ttk.Entry(
            split_btn_p, textvariable=self.hotkey_var, width=12, state="readonly"
        )
        self.hotkey_entry.pack(side="left", padx=5)
        self.hotkey_entry.bind("<Button-1>", self._start_hotkey_capture)
        self.hotkey_entry.bind("<Return>", lambda e: self._on_hotkey_change())
        self._capturing_hotkey = False

        ttk.Button(split_btn_p, text="+ 세로 분할", command=self._add_v_split).pack(
            side="right", padx=2
        )
        ttk.Button(split_btn_p, text="+ 가로 분할", command=self._add_h_split).pack(
            side="right", padx=2
        )
        ttk.Button(split_btn_p, text="초기화", command=self._reset_splits).pack(
            side="right", padx=2
        )

        # 정밀 수치 조정 영역 (미리보기 아래로 끌어올림)
        num_card = ttk.Frame(left_pane, style="Container.TFrame")
        num_card.pack(fill="x", pady=(0, 25))
        self.v_scroll_frame = ttk.Frame(num_card, style="Container.TFrame")
        self.v_scroll_frame.pack(side="top", fill="x")
        self.h_scroll_frame = ttk.Frame(num_card, style="Container.TFrame")
        self.h_scroll_frame.pack(side="top", fill="x", pady=2)

        # 3. Controls (Buttons - 스톱워치 스타일) (좌측 하단)
        controls = ttk.Frame(left_pane, style="Container.TFrame")
        controls.pack(fill="x")

        btn_start = tk.Button(
            controls,
            text="시작",
            bg=THEME["accent"],
            fg="#1a1a2e",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.start_callback,
        )
        btn_start.pack(side="left", expand=True, fill="x", padx=5)

        btn_auto = tk.Button(
            controls,
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
            controls,
            text="선택 지정",
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

        btn_stop = tk.Button(
            controls,
            text="중지 (Stop)",
            bg=THEME["error"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.stop_callback,
        )
        btn_stop.pack(side="left", expand=True, fill="x", padx=5)

        btn_help = tk.Button(
            controls,
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

        # 4. Laps (Treeview) (우측)
        laps_frame = ttk.Frame(right_pane, style="Container.TFrame")
        laps_frame.pack(fill="both", expand=True)

        ttk.Label(
            laps_frame,
            text="창 배정 기록 (Laps)",
            font=("Segoe UI", 10, "bold"),
            foreground=THEME["text_dim"],
        ).pack(anchor="w", pady=(0, 10))

        tree_container = ttk.Frame(laps_frame, style="Container.TFrame")
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_container, columns=("index", "title"), show="headings", height=15
        )
        self.tree.heading("index", text="랩 (슬롯)")
        self.tree.heading("title", text="창 제목")
        self.tree.column("index", width=80, anchor="center")
        self.tree.column("title", width=420)

        tree_sc = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_sc.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_sc.pack(side="right", fill="y")

        self.tree.bind("<Button-3>", self._on_tree_right_click)
        self.tree.bind("<Double-1>", lambda e: self._unbind_selected_slot())

        self._update_monitors()
        self.mon_combo.bind("<<ComboboxSelected>>", self._on_monitor_change)
        self._update_profile_combo()
        self.prof_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

    def set_status(self, text, status_type="info"):
        if not self.status_label:
            return

        color = THEME["text_dim"]
        prefix = "○"

        if status_type == "success":
            color = THEME["success"]
            prefix = "●"
        elif status_type == "error":
            color = THEME["error"]
            prefix = "×"
        elif status_type == "warning":
            color = THEME["warning"]
            prefix = "!"

        self.status_label.config(text=f"{prefix} {text}", fg=color)

    def _get_mon_cfg(self):
        return self.config

    def _get_current_mon_idx(self):
        try:
            val = self.mon_combo.get()
            return (
                int(val.split(":")[0]) if val else self.config.get("monitor_index", 0)
            )
        except:
            return self.config.get("monitor_index", 0)

    def _get_current_tracker(self):
        return self.tracker

    def _on_monitor_change(self, event):
        idx = self._get_current_mon_idx()
        self.config["monitor_index"] = idx
        self.tracker.monitor_index = idx
        self.tracker.update_layout()
        self._update_profile_combo()
        self.update_ui()
        save_config(self.config)
        if self.tracker.monitor_info:
            self._show_monitor_overlay(idx, self.tracker.monitor_info)

    def _update_monitors(self):
        monitors = get_all_monitors()
        self.mon_combo["values"] = [f"{i}: {m['name']}" for i, m in enumerate(monitors)]
        curr = self.config.get("monitor_index", 0)
        if curr < len(monitors):
            self.mon_combo.current(curr)
        else:
            self.mon_combo.current(0) if monitors else None

    def _update_profile_combo(self):
        names = list(self.profiles.keys())
        self.prof_combo["values"] = names
        curr = self.config.get("profile", "기본")
        if curr in names:
            self.prof_combo.set(curr)
        else:
            self.prof_combo.current(0) if names else None

    def _on_profile_change(self, event):
        name = self.prof_combo.get()
        self.config["profile"] = name
        self.tracker.update_layout()
        self.update_ui()
        save_config(self.config)

    def _add_profile(self):
        name = simpledialog.askstring(
            "새 프로필",
            "수정된 현재 레이아웃을 저장할 이름을 입력하세요:",
            parent=self.root,
        )
        if name:
            if name in self.profiles:
                messagebox.showwarning("오류", "이미 존재하는 이름입니다.")
                return
            # 현재 트래커가 사용 중인 실제 split 수치들을 프로필로 복사
            profile_name = self.config.get("profile", "기본")
            curr_profile = self.profiles.get(profile_name, self.profiles["기본"])
            self.profiles[name] = {
                "horizontal": list(curr_profile.get("horizontal", [])),
                "vertical": list(curr_profile.get("vertical", [])),
                "main_slot_index": self.config.get("main_slot_index", 0),
            }
            self.config["profile"] = name
            save_profiles(self.profiles)
            save_config(self.config)
            self._update_profile_combo()
            messagebox.showinfo("성공", f"'{name}' 프로필이 추가되었습니다.")

    def _save_current_profile(self):
        name = self.config.get("profile")
        messagebox.showinfo("알림", f"'{name}' 프로필: 분할선 조정 시 즉시 반영됩니다.")

    def _delete_profile(self):
        name = self.config.get("profile")
        if name == "기본":
            messagebox.showwarning("오류", "'기본' 프로필은 삭제할 수 없습니다.")
            return
        if messagebox.askyesno("삭제 확인", f"'{name}' 프로필을 삭제하시겠습니까?"):
            del self.profiles[name]
            self.config["profile"] = "기본"
            save_profiles(self.profiles)
            save_config(self.config)
            self._update_profile_combo()
            self._on_profile_change(None)

    def _on_canvas_press(self, event):
        if self.hover_split:
            self.dragging_split = self.hover_split
            return
        tracker = self._get_current_tracker()
        if not tracker:
            return
        for i, slot in enumerate(tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                cfg = self._get_mon_cfg()
                cfg["main_slot_index"] = i
                tracker.update_layout()
                self.update_ui()
                save_config(self.config)
                self._show_slot_overlay(i, tracker)
                break

    def _on_canvas_motion(self, event):
        if self.dragging_split:
            return
        cfg = self._get_mon_cfg()
        if not cfg:
            return
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        mx, my = event.x, event.y
        match_found = None
        for i, val in enumerate(p.get("vertical", [])):
            vx, _ = self._ratio_to_canvas(val, 0)
            if abs(mx - vx) < 6:
                match_found = {"type": "v", "index": i}
                self.preview_canvas.config(cursor="sb_h_double_arrow")
                break
        if not match_found:
            for i, val in enumerate(p.get("horizontal", [])):
                _, hy = self._ratio_to_canvas(0, val)
                if abs(my - hy) < 6:
                    match_found = {"type": "h", "index": i}
                    self.preview_canvas.config(cursor="sb_v_double_arrow")
                    break
        if not match_found:
            self.preview_canvas.config(cursor="arrow")
        self.hover_split = match_found

    def _on_canvas_drag(self, event):
        if not self.dragging_split:
            return
        stype, idx = self.dragging_split["type"], self.dragging_split["index"]
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        rx, ry = self._canvas_to_ratio(event.x, event.y)
        if stype == "v":
            p["vertical"][idx] = rx
            p["vertical"].sort()
        else:
            p["horizontal"][idx] = ry
            p["horizontal"].sort()
        tracker = self._get_current_tracker()
        if tracker:
            tracker.update_layout()
        self.update_ui()

    def _on_canvas_release(self, event):
        if self.dragging_split:
            save_profiles(self.profiles)
            self.dragging_split = None
            tracker = self._get_current_tracker()
            if tracker:
                tracker.reposition_all()

    def _add_v_split(self):
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        p.setdefault("vertical", []).append(0.5)
        p["vertical"].sort()
        tracker = self._get_current_tracker()
        if tracker:
            tracker.update_layout()
        self.update_ui()
        save_profiles(self.profiles)

    def _add_h_split(self):
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        p.setdefault("horizontal", []).append(0.5)
        p["horizontal"].sort()
        tracker = self._get_current_tracker()
        if tracker:
            tracker.update_layout()
        self.update_ui()
        save_profiles(self.profiles)

    def _reset_splits(self):
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        p["horizontal"] = []
        p["vertical"] = [0.33, 0.67]
        tracker = self._get_current_tracker()
        if tracker:
            tracker.update_layout()
        self.update_ui()
        save_profiles(self.profiles)

    def _on_manual_split_change(self, stype, index, entry_var):
        try:
            val = float(entry_var.get())
            if 0 < val < 1:
                cfg = self._get_mon_cfg()
                p = self.profiles.get(cfg["profile"], self.profiles["기본"])
                if stype == "v":
                    p["vertical"][index] = val
                    p["vertical"].sort()
                else:
                    p["horizontal"][index] = val
                    p["horizontal"].sort()
                tracker = self._get_current_tracker()
                if tracker:
                    tracker.update_layout()
                    tracker.reposition_all()
                self.update_ui()
                save_profiles(self.profiles)
        except ValueError:
            pass

    def _remove_split(self, stype, index):
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        if stype == "v":
            if index < len(p["vertical"]):
                del p["vertical"][index]
        else:
            if index < len(p["horizontal"]):
                del p["horizontal"][index]
        tracker = self._get_current_tracker()
        if tracker:
            tracker.update_layout()
            tracker.reposition_all()
        self.update_ui()
        save_profiles(self.profiles)

    def _update_numerical_inputs(self):
        if not self.v_scroll_frame:
            return
        for child in self.v_scroll_frame.winfo_children():
            child.destroy()
        for child in self.h_scroll_frame.winfo_children():
            child.destroy()

        cfg = self._get_mon_cfg()
        if not cfg:
            return
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])

        ttk.Label(self.v_scroll_frame, text=" 세로선: ", style="Dim.TLabel").pack(
            side="left", padx=(0, 5)
        )
        for i, val in enumerate(p.get("vertical", [])):
            var = tk.StringVar(value=f"{val:.3f}")
            f = ttk.Frame(self.v_scroll_frame, style="Card.TFrame")
            f.pack(side="left", padx=2)
            e = ttk.Entry(f, textvariable=var, width=6, font=("Segoe UI", 9))
            e.pack(side="left")
            e.bind(
                "<Return>",
                lambda evt, s="v", idx=i, v=var: self._on_manual_split_change(
                    s, idx, v
                ),
            )
            ttk.Button(
                f,
                text="×",
                width=2,
                command=lambda s="v", idx=i: self._remove_split(s, idx),
            ).pack(side="left", padx=(1, 0))

        ttk.Label(self.h_scroll_frame, text=" 가로선: ", style="Dim.TLabel").pack(
            side="left", padx=(0, 5)
        )
        for i, val in enumerate(p.get("horizontal", [])):
            var = tk.StringVar(value=f"{val:.3f}")
            f = ttk.Frame(self.h_scroll_frame, style="Card.TFrame")
            f.pack(side="left", padx=2)
            e = ttk.Entry(f, textvariable=var, width=6, font=("Segoe UI", 9))
            e.pack(side="left")
            e.bind(
                "<Return>",
                lambda evt, s="h", idx=i, v=var: self._on_manual_split_change(
                    s, idx, v
                ),
            )
            ttk.Button(
                f,
                text="×",
                width=2,
                command=lambda s="h", idx=i: self._remove_split(s, idx),
            ).pack(side="left", padx=(1, 0))

    def update_ui(self):
        if not self.preview_canvas:
            return
        self.preview_canvas.delete("all")
        tracker = self._get_current_tracker()
        cfg = self._get_mon_cfg()
        if not tracker or not cfg:
            return

        main_idx = cfg.get("main_slot_index", 0)
        # 슬롯 그리기
        for i, slot in enumerate(tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            is_main = i == main_idx

            fill_color = (
                THEME["surface"] if not is_main else "#004466"
            )  # 명확한 Accent 기반 강조색
            outline_color = THEME["accent"] if is_main else THEME["border"]
            width = 3 if is_main else 1

            self.preview_canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=width
            )

            # 인덱스 및 MAIN 텍스트 추가
            text_color = "white" if is_main else THEME["text_dim"]
            display_text = f"{i}\nMAIN" if is_main else str(i)
            font_style = (
                ("Segoe UI", 14, "bold") if is_main else ("Segoe UI", 12, "bold")
            )

            self.preview_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=display_text,
                fill=text_color,
                font=font_style,
                justify="center",
            )
        # 분할선 그리기
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        # 모니터 영역의 시작과 끝점 계산
        ox1, oy1 = self._ratio_to_canvas(0, 0)
        ox2, oy2 = self._ratio_to_canvas(1, 1)

        for v in p.get("vertical", []):
            vx, _ = self._ratio_to_canvas(v, 0)
            self.preview_canvas.create_line(
                vx, oy1, vx, oy2, fill=THEME["accent"], width=1, dash=(2, 2)
            )
        for h in p.get("horizontal", []):
            _, hy = self._ratio_to_canvas(0, h)
            self.preview_canvas.create_line(
                ox1, hy, ox2, hy, fill=THEME["accent"], width=1, dash=(2, 2)
            )

        self._update_numerical_inputs()
        self.tree.delete(*self.tree.get_children())
        for i, hwnd in enumerate(tracker.slot_hwnds):
            title = (
                win32gui.GetWindowText(hwnd)
                if hwnd and win32gui.IsWindow(hwnd)
                else "(비어 있음)"
            )
            self.tree.insert("", "end", values=(i, title))

    def _on_canvas_right_click(self, event):
        tracker = self._get_current_tracker()
        if not tracker:
            return
        target_idx = -1
        for i, slot in enumerate(tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                target_idx = i
                break
        if target_idx == -1:
            return

        # 컨텍스트 메뉴 생성
        menu = tk.Menu(self.root, tearoff=0)

        # 1. 창 할당 메뉴
        menu.add_command(
            label=f"슬롯 {target_idx}에 창 할당...",
            command=lambda: self._select_window_popup(
                target_idx, event.x_root, event.y_root
            ),
        )
        menu.add_command(
            label="메인 슬롯으로 지정", command=lambda: self._set_main_slot(target_idx)
        )
        menu.add_separator()

        # 2. 병합 관련 메뉴 (그리드 정보 필요)
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        num_cols = len(p.get("vertical", [])) + 1
        num_rows = len(p.get("horizontal", [])) + 1

        # 현재 슬롯이 어떤 베이스 인덱스들을 포함하는지 역산 (단순화를 위해 현재는 인덱스 기반 직접 병합 제안)
        menu.add_command(
            label="오른쪽 칸과 합치기",
            command=lambda: self._merge_slots(target_idx, "right"),
        )
        menu.add_command(
            label="아래쪽 칸과 합치기",
            command=lambda: self._merge_slots(target_idx, "bottom"),
        )
        menu.add_command(
            label="이 칸 병합 해제", command=lambda: self._unmerge_slot(target_idx)
        )
        menu.add_separator()
        menu.add_command(label="모든 병합 초기화", command=self._reset_all_merges)

        menu.post(event.x_root, event.y_root)

    def _set_main_slot(self, idx):
        cfg = self._get_mon_cfg()
        cfg["main_slot_index"] = idx
        self.tracker.update_layout()
        self.update_ui()
        save_config(self.config)

    def _select_window_popup(self, target_slot, px, py):
        tracker = self._get_current_tracker()
        windows = get_window_list(tracker.monitor_info)
        popup = tk.Toplevel(self.root)
        popup.title("창 선택")
        popup.attributes("-topmost", True)
        popup.geometry(f"3000x450+{px}+{py}")  # 임시 크게
        self._center_popup(popup, 300, 450)

        lb = tk.Listbox(popup)
        [lb.insert("end", t) for h, t in windows]
        lb.pack(fill="both", expand=True, padx=5, pady=5)

        def on_confirm():
            sel = lb.curselection()
            if sel:
                hwnd, _ = windows[sel[0]]
                for i, h in enumerate(tracker.slot_hwnds):
                    if h == hwnd:
                        tracker.slot_hwnds[i] = None
                tracker.slot_hwnds[target_slot] = hwnd
                tracker.reposition_all()
                self.update_ui()
                popup.destroy()

        ttk.Button(popup, text="선택 완료", command=on_confirm).pack(
            fill="x", padx=10, pady=5
        )
        lb.bind("<Double-1>", lambda e: on_confirm())

    def _merge_slots(self, slot_idx, direction):
        tracker = self._get_current_tracker()
        slot = tracker.slot_rects[slot_idx]
        base_indices = slot.get("base_indices", [slot_idx])

        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        num_cols = len(p.get("vertical", [])) + 1

        # 현재 슬롯의 경계에 인접한 베이스 인덱스 찾기
        target2 = -1
        if direction == "right":
            # 모든 베이스 인덱스 중 오른쪽에 빈 칸이 있는 것 찾기
            for b_idx in base_indices:
                if (b_idx + 1) % num_cols != 0:  # 오른쪽 끝이 아님
                    cand = b_idx + 1
                    if cand not in base_indices:
                        target2 = cand
                        break
        else:  # bottom
            for b_idx in base_indices:
                cand = b_idx + num_cols
                # cand가 범위를 넘지 않고 현재 병합에 포함되지 않아야 함
                if cand < (len(p.get("vertical", [])) + 1) * (
                    len(p.get("horizontal", [])) + 1
                ):
                    if cand not in base_indices:
                        target2 = cand
                        break

        if target2 != -1:
            merges = p.get("merges", [])
            # 기존 그룹이 있다면 합침, 없으면 새 그룹
            new_group = set(base_indices + [target2])

            # 기존 머지들 중 이들 중 하나라도 포함하는 그룹은 삭제 후 새 그룹으로 통합
            updated_merges = []
            for group in merges:
                if any(idx in new_group for idx in group):
                    new_group.update(group)
                else:
                    updated_merges.append(group)
            updated_merges.append(list(new_group))

            p["merges"] = updated_merges
            save_profiles(self.profiles)
            self.tracker.update_layout()
            self.update_ui()

    def _unmerge_slot(self, slot_idx):
        tracker = self._get_current_tracker()
        slot = tracker.slot_rects[slot_idx]
        base_indices = slot.get("base_indices", [slot_idx])

        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        merges = p.get("merges", [])

        # 이 슬롯의 베이스 인덱스들을 포함하는 모든 머지 그룹 삭제
        p["merges"] = [g for g in merges if not any(idx in base_indices for idx in g)]

        save_profiles(self.profiles)
        self.tracker.update_layout()
        self.update_ui()

    def _reset_all_merges(self):
        cfg = self._get_mon_cfg()
        p = self.profiles.get(cfg["profile"], self.profiles["기본"])
        p["merges"] = []
        save_profiles(self.profiles)
        self.tracker.update_layout()
        self.update_ui()

    def _get_canvas_coords(self, index):
        tracker = self._get_current_tracker()
        if not tracker or not tracker.monitor_info or index >= len(tracker.slot_rects):
            return (0, 0, 0, 0)
        rect, m = tracker.slot_rects[index]["rect"], tracker.monitor_info

        cw, ch = 540, 300
        scale = min(cw / m["width"], ch / m["height"]) * 0.95
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        x1, y1 = ox + (rect[0] - m["x"]) * scale, oy + (rect[1] - m["y"]) * scale
        x2, y2 = x1 + rect[2] * scale, y1 + rect[3] * scale
        return x1, y1, x2, y2

    def _canvas_to_ratio(self, cx, cy):
        # Convert canvas x, y back to 0.0~1.0 ratio
        cw, ch = 540, 300
        tracker = self._get_current_tracker()
        if not tracker or not tracker.monitor_info:
            return 0, 0
        m = tracker.monitor_info
        scale = min(cw / m["width"], ch / m["height"]) * 0.95
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        rx = (cx - ox) / draw_w
        ry = (cy - oy) / draw_h
        return max(0.01, min(0.99, rx)), max(0.01, min(0.99, ry))

    def _ratio_to_canvas(self, rx, ry):
        cw, ch = 540, 300
        tracker = self._get_current_tracker()
        if not tracker or not tracker.monitor_info:
            return rx * cw, ry * ch
        m = tracker.monitor_info
        scale = min(cw / m["width"], ch / m["height"]) * 0.95
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        return ox + rx * draw_w, oy + ry * draw_h

    # Old set_status removed (using line 214 version)

    def _show_slot_overlay(self, index, tracker):
        if not tracker or index >= len(tracker.slot_rects):
            return
        rect = tracker.slot_rects[index]["rect"]

        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        # Windows 투명도 및 최상단 설정
        overlay.attributes("-topmost", True, "-alpha", 0.7)
        from src.gui.theme import THEME

        overlay.configure(bg=THEME["accent"])

        lbl = tk.Label(
            overlay,
            text=f" SLOT {index} ",
            fg="#1a1a2e",
            bg=THEME["accent"],
            font=("Segoe UI", 48, "bold"),
        )
        lbl.place(relx=0.5, rely=0.5, anchor="center")

        x, y, w, h = rect
        overlay.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")

        # 1초 후 자동 제거
        self.root.after(1000, overlay.destroy)

    def _show_monitor_overlay(self, index, monitor):
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True, "-alpha", 0.8)

        # 디자인 개선된 라벨
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
        mx = monitor["x"] + (monitor["width"] - w) // 2
        my = monitor["y"] + (monitor["height"] - h) // 2
        overlay.geometry(f"{w}x{h}+{mx}+{my}")

        # 1.2초 후 자동 제거 (조금 더 길게)
        self.root.after(1200, overlay.destroy)

    def _center_popup(self, popup, width, height):
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        popup.geometry(f"{width}x{height}+{x}+{y}")

    def _on_unmap(self, event):
        # 루트 윈도우 자체가 unmap(최소화 등)될 때만 처리
        if event.widget == self.root and self.root.state() == "iconified":
            self.root.withdraw()

    def hide(self):
        if self.root:
            self.root.withdraw()

    def _auto_fill(self):
        count = self.tracker.auto_fill_all_slots()
        self.update_ui()
        self.set_status(f"● {count}개 슬롯 자동 할당됨", "success")

    def _on_gap_change(self):
        try:
            val = int(self.gap_var.get())
            self.config["gap"] = val
            self.tracker.update_layout()
            self.update_ui()
            self.tracker.reposition_all()
            save_config(self.config)
            self.set_status(f"● 간격 {val}px 적용됨", "success")
        except ValueError:
            messagebox.showwarning("오류", "숫자만 입력해 주세요.")

    def _on_hotkey_change(self):
        new_hotkey = self.hotkey_var.get().strip()
        if not new_hotkey:
            messagebox.showwarning("오류", "단축키를 입력해 주세요.")
            return

        if self.update_hotkey_callback:
            try:
                self.update_hotkey_callback(new_hotkey)
                self.set_status(f"● 핫키 '{new_hotkey}' 적용됨", "success")
            except Exception as e:
                messagebox.showerror(
                    "단축키 등록 오류", f"입력한 단축키 등록에 실패했습니다:\n{e}"
                )

    def _start_hotkey_capture(self, event):
        """키 입력 캡처 모드 시작"""
        if self._capturing_hotkey:
            return

        self._capturing_hotkey = True
        self.hotkey_var.set("키를 눌러주세요...")
        self.hotkey_entry.config(state="normal")
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.focus_set()

        # 키 이벤트 바인딩
        self.hotkey_entry.bind("<KeyPress>", self._on_key_press)
        self.hotkey_entry.bind("<KeyRelease>", self._on_key_release)

        # 캡처 상태 표시
        self.set_status("● 단축키 입력 대기 중...", "info")

    def _on_key_press(self, event):
        """키 입력 처리"""
        if not self._capturing_hotkey:
            return

        # 특수 키 처리
        key_symbols = {
            "Control_L": "Ctrl",
            "Control_R": "Ctrl",
            "Shift_L": "Shift",
            "Shift_R": "Shift",
            "Alt_L": "Alt",
            "Alt_R": "Alt",
            "Win_L": "Win",
            "Win_R": "Win",
            "Return": "Enter",
            "Escape": "Esc",
            "space": "Space",
            "Tab": "Tab",
            "BackSpace": "Backspace",
            "Delete": "Delete",
            "Insert": "Insert",
            "Home": "Home",
            "End": "End",
            "Prior": "PageUp",
            "Next": "PageDown",
            "Left": "Left",
            "Right": "Right",
            "Up": "Up",
            "Down": "Down",
        }

        keysym = event.keysym
        if keysym in key_symbols:
            key_name = key_symbols[keysym]
        elif len(keysym) == 1:
            key_name = keysym.upper()
        else:
            key_name = keysym

        modifier_order = ["Ctrl", "Shift", "Alt", "Win"]

        current_str = self.hotkey_var.get()
        if current_str == "키를 눌러주세요...":
            current_keys = []
        else:
            current_keys = current_str.split("+")

        if key_name in modifier_order:
            if key_name not in current_keys:
                current_keys.append(key_name)
        else:
            # 일반 키는 하나만 유지하고 기존 일반 키 교체
            current_keys = [k for k in current_keys if k in modifier_order]
            current_keys.append(key_name)

        # Modifier 순서대로 정렬
        mods = [k for k in modifier_order if k in current_keys]
        non_mods = [k for k in current_keys if k not in modifier_order]

        final_keys = mods + non_mods
        self.hotkey_var.set("+".join(final_keys))

        return "break"

    def _on_key_release(self, event):
        """키 릴리스 처리 - 입력 완료"""
        if not self._capturing_hotkey:
            return

        # 잠시 후 입력 완료 처리
        self.root.after(100, self._finish_hotkey_capture)
        return "break"

    def _finish_hotkey_capture(self):
        """키 입력 캡처 완료"""
        if not self._capturing_hotkey:
            return

        self._capturing_hotkey = False
        hotkey_str = self.hotkey_var.get().strip()

        # 유효성 검사
        if hotkey_str and hotkey_str != "키를 눌러주세요...":
            # 자동으로 적용 시도
            if self.update_hotkey_callback:
                try:
                    self.update_hotkey_callback(hotkey_str)
                    self.set_status(f"● 핫키 '{hotkey_str}' 적용됨", "success")
                except Exception as e:
                    messagebox.showerror(
                        "단축키 등록 오류", f"입력한 단축키 등록에 실패했습니다:\n{e}"
                    )
                    self.hotkey_var.set(self.config.get("hotkey", "Ctrl+Shift+T"))
            else:
                self.hotkey_var.set(hotkey_str)
        else:
            self.hotkey_var.set(self.config.get("hotkey", "Ctrl+Shift+T"))

        self.hotkey_entry.config(state="readonly")
        # 키 이벤트 바인딩 해제
        self.hotkey_entry.unbind("<KeyPress>")
        self.hotkey_entry.unbind("<KeyRelease>")

    # Removed unused _toggle_interactive

    def loop(self):
        """메인루프 실행 및 주기적 상태 체크 (Cycle 15)"""

        def check_assignment_mode():
            if not self.root:
                return
            if hasattr(self, "btn_interactive"):
                # 엔진에서 지정이 끝났는데 UI는 아직 '지정 중'인 경우
                if (
                    not self.tracker.is_assignment_mode
                    and self.btn_interactive.cget("text") != "클릭으로 지정 시작"
                ):
                    self.btn_interactive.config(text="클릭으로 지정 시작")
                    self.update_ui()
                    self.set_status("● 모든 슬롯 지정 완료", "success")
            self.root.after(500, check_assignment_mode)

        self.root.after(500, check_assignment_mode)
        self.root.mainloop()

    def quit(self):
        if self.root:
            self.root.quit()
            self.root.destroy()

    def _on_tree_right_click(self, event):
        """관리 현황 리스트 우클릭 메뉴 (Cycle 15)"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="이 슬롯 할당 해제", command=self._unbind_selected_slot)
        menu.post(event.x_root, event.y_root)

    def _unbind_selected_slot(self):
        """선택된 슬롯의 창 할당 해제 (Cycle 15)"""
        sel = self.tree.selection()
        if not sel:
            return

        # 첫 번째 열(번호)이 슬롯 인덱스
        val = self.tree.item(sel[0], "values")
        if not val:
            return

        idx = int(val[0])
        tracker = self._get_current_tracker()
        if tracker and idx < len(tracker.slot_hwnds):
            tracker.slot_hwnds[idx] = None
            tracker.reposition_all()
            self.update_ui()
            self.set_status(f"● 슬롯 {idx} 할당 해제됨", "info")

    def _show_help(self):
        """사용 방법 안내 팝업 (Cycle 15)"""
        help_text = (
            "■ Window Tiler 사용 방법 안내 ■\n\n"
            "1. 창 배정 원칙 (매우 중요!)\n"
            "   - 프로그램은 우측 '창 배정 기록'에 등록된 창들만 관리합니다. (등록 안 된 창은 안 섞임)\n"
            "   - 다음 3가지 방법으로 창을 배정해 주세요:\n"
            "     ① [자동 지정]: 현재 켜진 모든 창을 빈 슬롯에 꽉 채웁니다.\n"
            "     ② [선택 지정]: 창 목록을 보고 슬롯 순서대로 원하는 창만 골라 넣습니다.\n"
            "     ③ 캔버스 우클릭: 미리보기 화면의 빈 슬롯을 우클릭하여 하나씩 개별 배정합니다.\n\n"
            "2. 레이아웃과 메인 슬롯 (미리보기 화면)\n"
            "   - 분할선(하늘색 점선)을 드래그하여 슬롯 크기를 자유롭게 바꿀 수 있습니다.\n"
            "   - 특정 슬롯을 [왼쪽 클릭]하면 그 자리가 'MAIN(메인 슬롯)'이 됩니다.\n"
            "   - [오른쪽 클릭]하면 두 슬롯을 하나로 합치거나 초기화할 수 있습니다.\n\n"
            "3. 창 전환(스왑) 조작법 - 투명 덮개 기능\n"
            "   - 'MAIN 슬롯'이 아닌 조그만 조각(보조 슬롯)에 있는 창을 쓰고 싶다면, 마우스로 한 번만 클릭하세요.\n"
            "   - 클릭 즉시 MAIN 슬롯과 자리가 부드럽게 스왑됩니다.\n"
            "   - (오작동 방지를 위해 보조 슬롯 위에는 투명한 유리 덮개가 씌워져 있어, 안쪽 내용이 잘못 눌리지 않고 쾌적하게 전환됩니다.)\n\n"
            "4. 단축키 (핫키) 토글 기능\n"
            "   - 설정된 단축키(기본 Ctrl+Shift+T)를 누르면, 타일링 동작을 즉시 일시 정지하거나 재개할 수 있습니다.\n"
            "   - 좌측 화면의 '단축키' 입력란에 원하는 조합을 넣고 Enter를 눌러 변경 가능합니다.\n\n"
            "5. 시스템 트레이 (백그라운드 동작)\n"
            "   - 설정창을 'X'로 닫아도 프로그램은 우측 하단 시스템 트레이 아이콘으로 계속 동작합니다.\n"
            "   - 트레이 아이콘을 우클릭하여 설정창을 다시 열거나, 타일링 토글, 완전 종료를 할 수 있습니다."
        )
        messagebox.showinfo("Window Tiler 사용 방법", help_text)

    def _show_window_selector(self):
        """창 목록 선택 다이얼로그 열기 (Cycle 15)"""
        WindowSelector(self.root, self.tracker, self.update_ui, self.set_status)
