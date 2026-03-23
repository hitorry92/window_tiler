# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

# 스톱워치 스타일 테마
THEME = {
    "bg": "#1a1a2e",  # 스톱워치 배경색상 (Navy)
    "surface": "#252538",  # 유리 질감을 대체하는 단색 컨테이너 배경
    "border": "#3a3a55",  # 경계선
    "accent": "#00d4ff",  # 네온 블루 (Start 버튼 파스텔톤)
    "accent_hover": "#0099cc",
    "text": "#ffffff",  # 텍스트
    "text_dim": "#888888",  # 어두운 텍스트 (랩 타임 텍스트)
    "success": "#00d4ff",  # 진행중 (네온 블루)
    "warning": "#feca57",  # 경고 (Lap 버튼 라임/옐로우)
    "error": "#ff6b6b",  # 에러 (Stop 버튼 핑크/레드)
}


def setup_styles(root=None):
    style = ttk.Style()
    style.theme_use("clam")

    # 기본 구성요소
    style.configure("Bg.TFrame", background=THEME["bg"])
    style.configure("Container.TFrame", background=THEME["surface"])

    # 텍스트 스타일
    style.configure(
        "Header.TLabel",
        background=THEME["surface"],
        foreground=THEME["text"],
        font=("Segoe UI", 24, "bold"),
    )
    style.configure(
        "Container.TLabel",
        background=THEME["surface"],
        foreground=THEME["text"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "Dim.TLabel",
        background=THEME["surface"],
        foreground=THEME["text_dim"],
        font=("Segoe UI", 9),
    )

    # 기본 버튼 스타일 (회색 계열 - Reset 느낌)
    style.configure(
        "TButton",
        padding=6,
        font=("Segoe UI", 10),
        background="#444444",
        foreground=THEME["text"],
        borderwidth=0,
    )
    style.map(
        "TButton", background=[("active", "#555555")], foreground=[("active", "white")]
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground="#1e1e2d",
        background="#333",
        foreground=THEME["text"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#1e1e2d")],
        foreground=[("readonly", THEME["text"])],
    )

    if root:
        root.option_add("*TCombobox*Listbox.background", THEME["surface"])
        root.option_add("*TCombobox*Listbox.foreground", THEME["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", THEME["border"])
        root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # Treeview (Laps 스타일)
    style.configure(
        "Treeview",
        background="#1a1a2e",
        foreground=THEME["accent"],
        fieldbackground="#1a1a2e",
        rowheight=30,
        font=("Courier New", 12, "bold"),
    )
    style.configure(
        "Treeview.Heading",
        background="#252538",
        foreground=THEME["text_dim"],
        font=("Segoe UI", 10),
        relief="flat",
    )
    style.map("Treeview", background=[("selected", "#3a3a55")])

    return style
