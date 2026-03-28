# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

# [이해 포인트] 애플리케이션 전체에서 공통으로 사용할 색상표를 딕셔너리로 정의합니다.
# 한 곳에서 색상을 관리하면 나중에 테마를 변경하거나 유지보수하기가 매우 쉽습니다.
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
    # [핵심 로직] ttk.Style() 객체를 생성하여 위젯들의 전반적인 디자인(테마)을 설정합니다.
    style = ttk.Style()

    # [이해 포인트] 기본 윈도우 제공 테마 대신 커스터마이징이 자유로운 'clam' 테마를 기반으로 사용합니다.
    style.theme_use("clam")

    # 기본 구성요소
    # [핵심 로직] 각 위젯 타입(TFrame 등)의 배경색을 위에서 정의한 THEME 딕셔너리에서 가져와 설정합니다.
    style.configure("Bg.TFrame", background=THEME["bg"])
    style.configure("Container.TFrame", background=THEME["surface"])

    # 텍스트 스타일
    # [이해 포인트] 폰트의 종류, 크기, 색상 등을 미리 "Header.TLabel" 같이 묶어두고 나중에 위젯에서 가져다 사용합니다.
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
    # [핵심 로직] style.map()을 사용하면 마우스를 올렸을 때(active), 눌렀을 때 등 상태에 따라 바뀌는 색상을 지정할 수 있습니다.
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

    # [안전 장치] root 윈도우 객체가 정상적으로 전달되었을 때만 추가 옵션을 설정하도록 하여 에러를 방지합니다.
    if root:
        # [위험] 콤보박스의 드롭다운 리스트(Listbox)는 ttk가 아닌 기존 tk 위젯의 속성을 따릅니다.
        # 따라서 option_add를 통해 전역적인(global) tk 옵션으로 디자인을 덮어씌워야 테마가 정상 적용됩니다.
        root.option_add("*TCombobox*Listbox.background", THEME["surface"])
        root.option_add("*TCombobox*Listbox.foreground", THEME["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", THEME["border"])
        root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # Treeview (Laps 스타일)
    style.configure(
        "Treeview",
        background="#1a1a2e",
        foreground=THEME["text"],
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
