# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox


# [이해 포인트] 이 클래스는 사용자가 키보드를 눌러 단축키를 설정할 수 있게 해주는 커스텀 입력 위젯입니다.
class HotkeyEntryWidget(ttk.Entry):
    def __init__(
        self,
        master,
        initial_hotkey,
        on_hotkey_changed,
        set_status_callback=None,
        fallback_hotkey="Ctrl+Shift+T",
        **kwargs,
    ):
        # [이해 포인트] 위젯에 표시될 단축키 문자열을 저장하는 변수입니다.
        self.hotkey_var = tk.StringVar(value=initial_hotkey)
        super().__init__(
            master, textvariable=self.hotkey_var, state="readonly", **kwargs
        )

        self.on_hotkey_changed = on_hotkey_changed
        self.set_status_callback = set_status_callback
        self.fallback_hotkey = fallback_hotkey
        # [핵심 로직] 현재 단축키를 입력받고 있는 상태인지를 추적하는 플래그입니다.
        self._capturing_hotkey = False

        self.bind("<Button-1>", self._start_hotkey_capture)
        self.bind("<Return>", self._manual_confirm)

    def _set_status(self, msg, status_type):
        if self.set_status_callback:
            self.set_status_callback(msg, status_type)

    # [핵심 로직] 마우스 클릭 시 호출되어 단축키 캡처(입력 대기) 모드를 시작합니다.
    def _start_hotkey_capture(self, event):
        # [안전 장치] 이미 단축키를 입력받고 있는 중이라면 중복 실행을 막습니다.
        if self._capturing_hotkey:
            return

        self._capturing_hotkey = True
        self.hotkey_var.set("키를 눌러주세요...")
        self.config(state="normal")
        self.delete(0, tk.END)
        self.focus_set()

        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)

        self._set_status("● 단축키 입력 대기 중...", "info")

    # [핵심 로직] 사용자가 키보드를 누를 때마다 호출되어 누른 키를 인식하고 조합합니다.
    def _on_key_press(self, event):
        # [안전 장치] 캡처 모드가 아닐 때는 키 입력 이벤트를 무시합니다.
        if not self._capturing_hotkey:
            return

        # [이해 포인트] tkinter에서 인식하는 키 이름을 우리가 보기 편한 형태(Ctrl, Shift 등)로 변환하기 위한 맵핑 사전입니다.
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

        # [이해 포인트] 단축키가 표시될 때 일관된 순서(Ctrl -> Shift -> Alt -> Win -> 일반 키)를 유지하기 위한 리스트입니다.
        modifier_order = ["Ctrl", "Shift", "Alt", "Win"]
        current_str = self.hotkey_var.get()
        current_keys = (
            [] if current_str == "키를 눌러주세요..." else current_str.split("+")
        )

        if key_name in modifier_order:
            if key_name not in current_keys:
                current_keys.append(key_name)
        else:
            current_keys = [k for k in current_keys if k in modifier_order]
            current_keys.append(key_name)

        mods = [k for k in modifier_order if k in current_keys]
        non_mods = [k for k in current_keys if k not in modifier_order]

        self.hotkey_var.set("+".join(mods + non_mods))
        return "break"

    # [핵심 로직] 키보드에서 손을 뗄 때 호출되며, 단축키 입력이 완료되었음을 처리합니다.
    def _on_key_release(self, event):
        if not self._capturing_hotkey:
            return
        # [이해 포인트] 0.1초 대기 후 캡처 완료 처리를 실행하여 여러 키가 동시에 떼어질 때의 오작동을 방지합니다.
        self.after(100, self._finish_hotkey_capture)
        return "break"

    # [핵심 로직] 단축키 캡처를 종료하고, 입력된 단축키를 시스템에 적용하는 함수입니다.
    def _finish_hotkey_capture(self):
        if not self._capturing_hotkey:
            return

        self._capturing_hotkey = False
        hotkey_str = self.hotkey_var.get().strip()

        if hotkey_str and hotkey_str != "키를 눌러주세요...":
            if self.on_hotkey_changed:
                # [위험] 단축키를 시스템에 등록하는 과정에서 다른 프로그램과 충돌이 발생하거나 권한 문제가 있을 수 있습니다.
                try:
                    self.on_hotkey_changed(hotkey_str)
                    self._set_status(f"● 핫키 '{hotkey_str}' 적용됨", "success")
                except Exception as e:
                    messagebox.showerror(
                        "단축키 등록 오류", f"입력한 단축키 등록에 실패했습니다:\n{e}"
                    )
                    # [안전 장치] 등록 실패 시, 위젯의 표시를 기본(대체) 단축키로 되돌립니다.
                    self.hotkey_var.set(self.fallback_hotkey)
            else:
                self.hotkey_var.set(hotkey_str)
        else:
            self.hotkey_var.set(self.fallback_hotkey)

        self.config(state="readonly")
        self.unbind("<KeyPress>")
        self.unbind("<KeyRelease>")

    # [핵심 로직] Enter 키를 눌렀을 때(수동 확인) 입력된 단축키를 적용하는 함수입니다.
    def _manual_confirm(self, event):
        new_hotkey = self.hotkey_var.get().strip()
        if not new_hotkey or new_hotkey == "키를 눌러주세요...":
            messagebox.showwarning("오류", "단축키를 입력해 주세요.")
            return

        if self.on_hotkey_changed:
            try:
                self.on_hotkey_changed(new_hotkey)
                self._set_status(f"● 핫키 '{new_hotkey}' 적용됨", "success")
            except Exception as e:
                messagebox.showerror(
                    "단축키 등록 오류", f"입력한 단축키 등록에 실패했습니다:\n{e}"
                )
