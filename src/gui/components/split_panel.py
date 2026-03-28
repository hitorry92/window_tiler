import tkinter as tk
from tkinter import ttk, messagebox
from src.gui.theme import THEME
from src.gui.hotkey_entry import HotkeyEntryWidget
from src.app_config import save_config


class SplitPanel(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, style="Container.TFrame", **kwargs)
        self.app = app

        # 간격
        ttk.Label(self, text="⟷ 간격:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        self.gap_var = tk.StringVar(value=str(self.app.config.get("gap", 0)))
        gap_e = ttk.Entry(self, textvariable=self.gap_var, width=5)
        gap_e.pack(side="left", padx=5)
        gap_e.bind("<Return>", lambda e: self._on_gap_change())

        # 핫키
        ttk.Label(self, text="🔢 단축키:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        fallback = self.app.config.get("hotkey", "Ctrl+Shift+T")
        self.hotkey_entry = HotkeyEntryWidget(
            self,
            initial_hotkey=fallback,
            on_hotkey_changed=self.app.update_hotkey_callback,
            set_status_callback=self.app.set_status,
            fallback_hotkey=fallback,
            width=12,
        )
        self.hotkey_entry.pack(side="left", padx=5)

        ttk.Button(self, text="+ 세로 분할", command=self._add_v_split).pack(
            side="right", padx=2
        )
        ttk.Button(self, text="+ 가로 분할", command=self._add_h_split).pack(
            side="right", padx=2
        )
        ttk.Button(self, text="초기화", command=self._reset_splits).pack(
            side="right", padx=2
        )

    def _on_gap_change(self):
        try:
            val = int(self.gap_var.get())
            self.app.config["gap"] = val
            self.app.tracker.update_layout()
            self.app.update_ui()
            self.app.tracker.reposition_all()
            save_config(self.app.config)
            self.app.set_status(f"● 간격 {val}px 적용됨", "success")
        except ValueError:
            messagebox.showwarning("오류", "숫자만 입력해 주세요.")

    def _get_current_profile(self):
        idx_str = str(self.app.config.get("monitor_index", 0))
        mon_config = self.app.config.get("monitor_configs", {}).get(idx_str, {})
        p_name = mon_config.get("profile", "기본")
        return self.app.profiles.get(p_name, self.app.profiles.get("기본", {}))

    def _add_v_split(self):
        p = self._get_current_profile()
        p.setdefault("vertical", []).append(0.5)
        p["vertical"].sort()
        self.app.request_layout_update(reposition=False)

    def _add_h_split(self):
        p = self._get_current_profile()
        p.setdefault("horizontal", []).append(0.5)
        p["horizontal"].sort()
        self.app.request_layout_update(reposition=False)

    def _reset_splits(self):
        p = self._get_current_profile()
        p["horizontal"] = []
        p["vertical"] = [0.33, 0.67]
        self.app.request_layout_update(reposition=False)


class NumericalInputsPanel(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, style="Container.TFrame", **kwargs)
        self.app = app

        self.v_scroll_frame = ttk.Frame(self, style="Container.TFrame")
        self.v_scroll_frame.pack(side="top", fill="x")
        self.h_scroll_frame = ttk.Frame(self, style="Container.TFrame")
        self.h_scroll_frame.pack(side="top", fill="x", pady=2)

    def _get_current_profile(self):
        idx_str = str(self.app.config.get("monitor_index", 0))
        mon_config = self.app.config.get("monitor_configs", {}).get(idx_str, {})
        p_name = mon_config.get("profile", "기본")
        return self.app.profiles.get(p_name, self.app.profiles.get("기본", {}))

    def update_inputs(self):
        for child in self.v_scroll_frame.winfo_children():
            child.destroy()
        for child in self.h_scroll_frame.winfo_children():
            child.destroy()

        if not self.app.config:
            return

        p = self._get_current_profile()

        ttk.Label(self.v_scroll_frame, text=" 세로선: ", style="Dim.TLabel").pack(
            side="left", padx=(0, 5)
        )
        for i, val in enumerate(p.get("vertical", [])):
            self._create_entry(self.v_scroll_frame, val, "v", i)

        ttk.Label(self.h_scroll_frame, text=" 가로선: ", style="Dim.TLabel").pack(
            side="left", padx=(0, 5)
        )
        for i, val in enumerate(p.get("horizontal", [])):
            self._create_entry(self.h_scroll_frame, val, "h", i)

    def _create_entry(self, parent, val, stype, idx):
        var = tk.StringVar(value=f"{val:.3f}")
        f = ttk.Frame(parent, style="Card.TFrame")
        f.pack(side="left", padx=2)
        e = ttk.Entry(f, textvariable=var, width=6, font=("Segoe UI", 9))
        e.pack(side="left")
        e.bind(
            "<Return>",
            lambda evt, s=stype, i=idx, v=var: self._on_manual_change(s, i, v),
        )
        ttk.Button(
            f,
            text="×",
            width=2,
            command=lambda s=stype, i=idx: self._remove_split(s, i),
        ).pack(side="left", padx=(1, 0))

    def _on_manual_change(self, stype, index, entry_var):
        try:
            val = float(entry_var.get())
            if 0 < val < 1:
                p = self._get_current_profile()
                if stype == "v":
                    p["vertical"][index] = val
                    p["vertical"].sort()
                else:
                    p["horizontal"][index] = val
                    p["horizontal"].sort()
                self.app.request_layout_update(reposition=True)
        except ValueError:
            pass

    def _remove_split(self, stype, index):
        p = self._get_current_profile()
        if stype == "v":
            if index < len(p.get("vertical", [])):
                del p["vertical"][index]
        else:
            if index < len(p.get("horizontal", [])):
                del p["horizontal"][index]
        self.app.request_layout_update(reposition=True)
