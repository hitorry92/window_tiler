import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from src.app_config import save_config, save_profiles, load_profiles
from src.win_utils import get_all_monitors
from src.gui.theme import THEME


class ProfilePanel(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, style="Container.TFrame", **kwargs)
        self.app = app

        ttk.Label(self, text="💻 모니터:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        self.mon_combo = ttk.Combobox(self, state="readonly", width=15)
        self.mon_combo.pack(side="left", padx=(0, 15))
        self.mon_combo.bind("<<ComboboxSelected>>", self._on_monitor_change)

        ttk.Label(self, text="👤 프로필:", style="Container.TLabel").pack(
            side="left", padx=(0, 5)
        )
        self.prof_combo = ttk.Combobox(self, state="readonly", width=12)
        self.prof_combo.pack(side="left", padx=(0, 5))
        self.prof_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        ttk.Button(self, text="+", width=2, command=self._add_profile).pack(
            side="left", padx=1
        )
        ttk.Button(self, text="저장", width=4, command=self._save_current_profile).pack(
            side="left", padx=1
        )
        ttk.Button(self, text="삭제", width=4, command=self._delete_profile).pack(
            side="left", padx=1
        )

        # 모드 선택 스위치
        ttk.Label(self, text="  | 🔄 모드 전환:", style="Container.TLabel").pack(
            side="left", padx=(5, 2)
        )
        self.mode_combo = ttk.Combobox(self, state="readonly", width=10)
        self.mode_combo["values"] = ["로컬 모드", "글로벌 모드"]
        current_mode = self.app.config.get("swap_mode", "local")
        self.mode_combo.set("글로벌 모드" if current_mode == "global" else "로컬 모드")
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        self.mode_combo.pack(side="left", padx=(0, 10))

        self.status_label = tk.Label(
            self,
            text="○ 대기 중",
            fg=THEME["text_dim"],
            bg=THEME["surface"],
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="right")

        self.update_monitors()
        self.update_profile_combo()

    def _on_mode_change(self, event):
        val = self.mode_combo.get()
        mode = "global" if val == "글로벌 모드" else "local"
        self.app.config["swap_mode"] = mode
        save_config(self.app.config)
        self.set_status(f"● 모드 전환: {val} 적용됨", "success")
        self.app.update_ui()

    def set_status(self, text, status_type="info"):
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

    def _get_current_mon_idx(self):
        try:
            val = self.mon_combo.get()
            return (
                int(val.split(":")[0])
                if val
                else self.app.config.get("monitor_index", 0)
            )
        except:
            return self.app.config.get("monitor_index", 0)

    def _on_monitor_change(self, event):
        idx = self._get_current_mon_idx()
        self.app.config["monitor_index"] = idx

        # [핵심 로직] main.py(앱)에 선택된 활성 모니터 인덱스 동기화
        if hasattr(self.app, "active_monitor_index"):
            self.app.active_monitor_index = idx

        tracker = self.app.tracker
        if tracker:
            tracker.update_layout()

        self.update_profile_combo()
        self.app.update_ui()
        save_config(self.app.config)

        if tracker and tracker.monitor_info:
            self.app._show_monitor_overlay(idx, tracker.monitor_info)

    def update_monitors(self):
        monitors = get_all_monitors()
        self.mon_combo["values"] = [f"{i}: {m['name']}" for i, m in enumerate(monitors)]
        curr = self.app.config.get("monitor_index", 0)
        if curr < len(monitors):
            self.mon_combo.current(curr)
        else:
            if monitors:
                self.mon_combo.current(0)

    def update_profile_combo(self):
        names = list(self.app.profiles.keys())
        self.prof_combo["values"] = names

        idx_str = str(self._get_current_mon_idx())
        curr = (
            self.app.config.get("monitor_configs", {})
            .get(idx_str, {})
            .get("profile", "기본")
        )

        if curr in names:
            self.prof_combo.set(curr)
        else:
            if names:
                self.prof_combo.current(0)
        self.app.profile_modified = False
        self.update_profile_combo_display()

    def update_profile_combo_display(self):
        idx_str = str(self._get_current_mon_idx())
        current_name = (
            self.app.config.get("monitor_configs", {})
            .get(idx_str, {})
            .get("profile", "기본")
        )
        display_name = f"{current_name}*" if self.app.profile_modified else current_name
        current_values = list(self.prof_combo["values"])

        try:
            real_name_index = -1
            for i, v in enumerate(current_values):
                if v.strip("*") == current_name:
                    real_name_index = i
                    break
            if real_name_index != -1:
                current_values[real_name_index] = display_name
                self.prof_combo["values"] = current_values
                self.prof_combo.set(display_name)
            else:
                self.prof_combo.set(display_name)
        except tk.TclError:
            self.prof_combo.set(display_name)

    def _on_profile_change(self, event):
        idx_str = str(self._get_current_mon_idx())
        current_profile = (
            self.app.config.get("monitor_configs", {})
            .get(idx_str, {})
            .get("profile", "기본")
        )

        if self.app.profile_modified:
            if not messagebox.askyesno(
                "변경사항 저장",
                "저장되지 않은 변경사항이 있습니다. 저장하지 않고 전환하시겠습니까?",
                parent=self.winfo_toplevel(),
            ):
                self.prof_combo.set(current_profile)
                return

        self.app.profiles.clear()
        self.app.profiles.update(load_profiles())

        name = self.prof_combo.get().strip("*")
        self.app.config["profile"] = name  # Legacy support

        if "monitor_configs" not in self.app.config:
            self.app.config["monitor_configs"] = {}
        if idx_str not in self.app.config["monitor_configs"]:
            self.app.config["monitor_configs"][idx_str] = {}

        self.app.config["monitor_configs"][idx_str]["profile"] = name

        tracker = self.app.tracker
        if tracker:
            tracker.monitor_config["profile"] = name

        self.app.request_layout_update(reposition=True)
        save_config(self.app.config)
        self.app.profile_modified = False
        self.update_profile_combo_display()

    def _add_profile(self):
        name = simpledialog.askstring(
            "새 프로필",
            "수정된 현재 레이아웃을 저장할 이름을 입력하세요:",
            parent=self.winfo_toplevel(),
        )
        if name:
            if name in self.app.profiles:
                messagebox.showwarning("오류", "이미 존재하는 이름입니다.")
                return

            idx_str = str(self._get_current_mon_idx())
            profile_name = (
                self.app.config.get("monitor_configs", {})
                .get(idx_str, {})
                .get("profile", "기본")
            )
            curr_profile = self.app.profiles.get(
                profile_name, self.app.profiles.get("기본", {})
            )
            self.app.profiles[name] = {
                "horizontal": list(curr_profile.get("horizontal", [])),
                "vertical": list(curr_profile.get("vertical", [])),
                "main_slot_index": self.app.config.get("monitor_configs", {})
                .get(idx_str, {})
                .get("main_slot_index", 0),
            }

            self.app.config["profile"] = name  # Legacy support
            if "monitor_configs" not in self.app.config:
                self.app.config["monitor_configs"] = {}
            if idx_str not in self.app.config["monitor_configs"]:
                self.app.config["monitor_configs"][idx_str] = {}
            self.app.config["monitor_configs"][idx_str]["profile"] = name

            tracker = self.app.tracker
            if tracker:
                tracker.monitor_config["profile"] = name

            save_profiles(self.app.profiles)
            save_config(self.app.config)

            self.update_profile_combo()
            self.app.profile_modified = False
            self.update_profile_combo_display()
            messagebox.showinfo("성공", f"'{name}' 프로필이 추가되었습니다.")

    def _save_current_profile(self):
        save_profiles(self.app.profiles)
        self.app.profile_modified = False
        self.update_profile_combo_display()
        self.set_status("● 프로필이 저장되었습니다.", "success")

    def _delete_profile(self):
        idx_str = str(self._get_current_mon_idx())
        name = (
            self.app.config.get("monitor_configs", {})
            .get(idx_str, {})
            .get("profile", "기본")
        )

        if name == "기본":
            messagebox.showwarning("오류", "'기본' 프로필은 삭제할 수 없습니다.")
            return
        if messagebox.askyesno("삭제 확인", f"'{name}' 프로필을 삭제하시겠습니까?"):
            if name in self.app.profiles:
                del self.app.profiles[name]

            self.app.config["profile"] = "기본"
            if (
                "monitor_configs" in self.app.config
                and idx_str in self.app.config["monitor_configs"]
            ):
                self.app.config["monitor_configs"][idx_str]["profile"] = "기본"

            save_profiles(self.app.profiles)
            save_config(self.app.config)

            self.update_profile_combo()
            self._on_profile_change(None)
            self.app.profile_modified = False
            self.update_profile_combo_display()
