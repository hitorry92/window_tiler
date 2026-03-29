# -*- coding: utf-8 -*-
import tkinter as tk
from .theme import THEME
from .window_selector import WindowSelector
from ..app_config import (
    DEFAULT_SWAP_MODE,
    DEFAULT_PROFILE,
    get_config_value,
    PREVIEW_MARGIN_RATIO,
)


# [이해 포인트] 화면 분할 레이아웃을 시각적으로 보여주고 조작(드래그, 클릭 등)할 수 있게 해주는 Tkinter Canvas 커스텀 클래스입니다.
class PreviewCanvas(tk.Canvas):
    def __init__(
        self,
        master,
        tracker,
        config,
        profiles,
        on_layout_update,
        on_profile_modified,
        on_save_config,
        on_status_update,
        on_show_window_selector,
        **kwargs,
    ):
        super().__init__(
            master,
            bg="#0a0a0e",
            highlightthickness=2,
            highlightbackground=THEME["accent"],
            cursor="arrow",
            **kwargs,
        )
        self.tracker = tracker
        self.config = config
        self.profiles = profiles

        # Callbacks (외부에서 주입받은 이벤트 핸들러들)
        self.on_layout_update = on_layout_update
        self.on_profile_modified = on_profile_modified
        self.on_save_config = on_save_config
        self.on_status_update = on_status_update
        self.on_show_window_selector = on_show_window_selector

        # State
        self.hover_split = None
        self.dragging_split = None

        # Bind events
        # [이해 포인트] 마우스 동작(클릭, 드래그, 이동, 우클릭)에 대한 이벤트를 연결합니다.
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-3>", self._on_right_click)

    # [핵심 로직] 현재 모니터의 설정을 가져오는 헬퍼 함수
    def _get_mon_config(self):
        idx_str = str(self.config.get("monitor_index", 0))
        return self.config.get("monitor_configs", {}).get(idx_str, {})

    # [핵심 로직] 현재 프로필 설정과 트래커 데이터를 바탕으로 캔버스 위에 슬롯과 분할선을 다시 그립니다.
    def update_drawing(self):
        self.delete("all")
        if not self.tracker or not self.config:
            return

        mon_config = self._get_mon_config()
        main_idx = mon_config.get("main_slot_index", 0)

        swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)
        g_mon = get_config_value(self.config, "global_main_monitor", 0)
        g_slot = get_config_value(self.config, "global_main_slot", 0)
        is_global_main_monitor = (
            swap_mode == "global" and self.tracker.monitor_index == g_mon
        )

        # 슬롯 그리기
        for i, slot in enumerate(self.tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            is_local_main = i == main_idx
            is_global_main = is_global_main_monitor and i == g_slot

            # [수정] 글로벌 모드일 경우 각 모니터의 로컬 메인(MAIN) 표시는 무시하고 오직 GLOBAL MAIN만 강조합니다.
            if swap_mode == "global":
                is_main_display = is_global_main
                fill_color = "#660044" if is_global_main else THEME["surface"]
                display_text = f"{i}\nGLOBAL MAIN" if is_global_main else str(i)
            else:
                is_main_display = is_local_main
                fill_color = "#004466" if is_local_main else THEME["surface"]
                display_text = f"{i}\nMAIN" if is_local_main else str(i)

            outline_color = THEME["accent"] if is_main_display else THEME["border"]
            width = 3 if is_main_display else 1

            self.create_rectangle(
                x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=width
            )

            text_color = "white" if is_main_display else THEME["text_dim"]

            font_style = (
                ("Segoe UI", 14, "bold")
                if is_main_display
                else ("Segoe UI", 12, "bold")
            )

            self.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=display_text,
                fill=text_color,
                font=font_style,
                justify="center",
            )

        # 분할선 그리기
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )
        ox1, oy1 = self._ratio_to_canvas(0, 0)
        ox2, oy2 = self._ratio_to_canvas(1, 1)

        for v in p.get("vertical", []):
            vx, _ = self._ratio_to_canvas(v, 0)
            self.create_line(
                vx, oy1, vx, oy2, fill=THEME["accent"], width=1, dash=(2, 2)
            )

        for h in p.get("horizontal", []):
            _, hy = self._ratio_to_canvas(0, h)
            self.create_line(
                ox1, hy, ox2, hy, fill=THEME["accent"], width=1, dash=(2, 2)
            )

    # [이해 포인트] 실제 모니터 상의 좌표를 캔버스 비율에 맞게 축소/변환합니다. (PREVIEW_MARGIN_RATIO를 곱해 여백을 줌)
    def _get_canvas_coords(self, index):
        if (
            not self.tracker
            or not self.tracker.monitor_info
            or index >= len(self.tracker.slot_rects)
        ):
            return (0, 0, 0, 0)

        rect = self.tracker.slot_rects[index]["rect"]
        m = self.tracker.monitor_info
        cw, ch = int(self["width"]), int(self["height"])

        scale = min(cw / m["width"], ch / m["height"]) * PREVIEW_MARGIN_RATIO
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        x1 = ox + (rect[0] - m["x"]) * scale
        y1 = oy + (rect[1] - m["y"]) * scale
        x2 = x1 + rect[2] * scale
        y2 = y1 + rect[3] * scale
        return x1, y1, x2, y2

    # [핵심 로직] 캔버스 상의 클릭 좌표(픽셀)를 전체 대비 비율(0~1)로 변환합니다.
    def _canvas_to_ratio(self, cx, cy):
        cw, ch = int(self["width"]), int(self["height"])
        if not self.tracker or not self.tracker.monitor_info:
            return 0, 0
        m = self.tracker.monitor_info
        scale = min(cw / m["width"], ch / m["height"]) * PREVIEW_MARGIN_RATIO
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        rx = (cx - ox) / draw_w
        ry = (cy - oy) / draw_h
        # [안전 장치] 비율이 0~1 범위를 벗어나지 않도록 클램핑(Clamping) 처리합니다.
        return max(0.01, min(0.99, rx)), max(0.01, min(0.99, ry))

    # [핵심 로직] 비율(0~1) 정보를 다시 캔버스 상의 픽셀 좌표로 변환합니다.
    def _ratio_to_canvas(self, rx, ry):
        cw, ch = int(self["width"]), int(self["height"])
        if not self.tracker or not self.tracker.monitor_info:
            return rx * cw, ry * ch
        m = self.tracker.monitor_info
        scale = min(cw / m["width"], ch / m["height"]) * PREVIEW_MARGIN_RATIO
        draw_w, draw_h = m["width"] * scale, m["height"] * scale
        ox, oy = (cw - draw_w) / 2, (ch - draw_h) / 2

        return ox + rx * draw_w, oy + ry * draw_h

    # [이해 포인트] 마우스 좌클릭 시 발생하는 이벤트 처리 (분할선 드래그 시작 또는 메인 슬롯 변경)
    def _on_press(self, event):
        if self.hover_split:
            self.dragging_split = self.hover_split
            return

        if not self.tracker:
            return

        mon_config = self._get_mon_config()
        swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)

        for i, slot in enumerate(self.tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if swap_mode == "global":
                    self.config["global_main_monitor"] = self.tracker.monitor_index
                    self.config["global_main_slot"] = i
                else:
                    mon_config["main_slot_index"] = i
                    # Legacy update
                    self.config["main_slot_index"] = i

                self.tracker.update_layout()
                self.update_drawing()
                self.on_save_config()
                self._show_slot_overlay(i)
                self.on_layout_update(reposition=False)  # trigger UI updates
                break

    # [이해 포인트] 마우스 이동 시 분할선 위에 마우스가 있는지 확인하여 마우스 커서 모양을 변경합니다.
    def _on_motion(self, event):
        if self.dragging_split:
            return

        mon_config = self._get_mon_config()
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )
        mx, my = event.x, event.y
        match_found = None

        # [위험] 픽셀 오차 허용 범위가 6픽셀로 고정되어 있어, DPI나 화면 해상도 설정에 따라 클릭이 어려울 수도 있습니다.
        for i, val in enumerate(p.get("vertical", [])):
            vx, _ = self._ratio_to_canvas(val, 0)
            if abs(mx - vx) < 6:
                match_found = {"type": "v", "index": i}
                self.config["cursor"] = "sb_h_double_arrow"
                break

        if not match_found:
            for i, val in enumerate(p.get("horizontal", [])):
                _, hy = self._ratio_to_canvas(0, val)
                if abs(my - hy) < 6:
                    match_found = {"type": "h", "index": i}
                    self.config["cursor"] = "sb_v_double_arrow"
                    break

        if not match_found:
            self.config["cursor"] = "arrow"

        self.hover_split = match_found

    # [핵심 로직] 분할선을 드래그할 때 실행되며, 프로필 내의 수직/수평 분할 비율을 즉시 업데이트합니다.
    def _on_drag(self, event):
        if not self.dragging_split:
            return

        stype, idx = self.dragging_split["type"], self.dragging_split["index"]
        mon_config = self._get_mon_config()
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )
        rx, ry = self._canvas_to_ratio(event.x, event.y)

        # [안전 장치] 분할선 위치 변경 후 리스트를 정렬하여 선이 교차하거나 순서가 꼬이는 것을 방지합니다.
        if stype == "v":
            p["vertical"][idx] = rx
            p["vertical"].sort()
        else:
            p["horizontal"][idx] = ry
            p["horizontal"].sort()

        if self.tracker:
            self.tracker.update_layout()

        self.update_drawing()
        self.on_profile_modified()

    def _on_release(self, event):
        if self.dragging_split:
            self.dragging_split = None
            self.on_layout_update(reposition=True)

    # [핵심 로직] 슬롯에서 마우스 우클릭을 했을 때 창 할당, 병합(Merge) 등의 기능을 제공하는 컨텍스트 메뉴를 표시합니다.
    def _on_right_click(self, event):
        if not self.tracker:
            return

        target_idx = -1
        for i, slot in enumerate(self.tracker.slot_rects):
            x1, y1, x2, y2 = self._get_canvas_coords(i)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                target_idx = i
                break

        if target_idx == -1:
            return

        menu = tk.Menu(self.winfo_toplevel(), tearoff=0)
        menu.add_command(
            label=f"슬롯 {target_idx}에 창 할당...",
            command=lambda: self.on_show_window_selector(target_idx),
        )

        swap_mode = get_config_value(self.config, "swap_mode", DEFAULT_SWAP_MODE)
        if swap_mode == "global":
            menu.add_command(
                label="★ 전역 메인 슬롯으로 지정 ★",
                command=lambda: self._set_global_main_slot(target_idx),
            )
        else:
            menu.add_command(
                label="메인 슬롯으로 지정",
                command=lambda: self._set_main_slot(target_idx),
            )

        menu.add_separator()
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
        mon_config = self._get_mon_config()
        mon_config["main_slot_index"] = idx
        self.config["main_slot_index"] = idx  # Legacy fallback

        self.tracker.update_layout()
        self.update_drawing()
        self.on_save_config()
        self.on_layout_update(reposition=False)

    def _set_global_main_slot(self, idx):
        self.config["global_main_monitor"] = self.tracker.monitor_index
        self.config["global_main_slot"] = idx
        self.tracker.update_layout()
        self.update_drawing()
        self.on_save_config()
        self.on_layout_update(reposition=False)

    # [핵심 로직] 지정된 슬롯을 인접한(우측 혹은 하단) 슬롯과 병합하여 하나로 만듭니다.
    def _merge_slots(self, slot_idx, direction):
        slot = self.tracker.slot_rects[slot_idx]
        base_indices = slot.get("base_indices", [slot_idx])

        mon_config = self._get_mon_config()
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )

        num_cols = len(p.get("vertical", [])) + 1

        # [위험] 그리드 형태의 배열 구조를 가정하고 인덱스 덧셈을 수행하므로, 레이아웃 구조가 복잡해지면 버그가 발생할 수 있습니다.
        target2 = -1
        if direction == "right":
            for b_idx in base_indices:
                if (b_idx + 1) % num_cols != 0:
                    cand = b_idx + 1
                    if cand not in base_indices:
                        target2 = cand
                        break
        else:
            for b_idx in base_indices:
                cand = b_idx + num_cols
                if cand < (len(p.get("vertical", [])) + 1) * (
                    len(p.get("horizontal", [])) + 1
                ):
                    if cand not in base_indices:
                        target2 = cand
                        break

        if target2 != -1:
            merges = p.get("merges", [])
            new_group = set(base_indices + [target2])
            updated_merges = []
            for group in merges:
                if any(idx in new_group for idx in group):
                    new_group.update(group)
                else:
                    updated_merges.append(group)
            updated_merges.append(list(new_group))
            p["merges"] = updated_merges
            self.on_layout_update(reposition=True)

    def _unmerge_slot(self, slot_idx):
        slot = self.tracker.slot_rects[slot_idx]
        base_indices = slot.get("base_indices", [slot_idx])

        mon_config = self._get_mon_config()
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )

        merges = p.get("merges", [])
        p["merges"] = [g for g in merges if not any(idx in base_indices for idx in g)]
        self.on_layout_update(reposition=True)

    def _reset_all_merges(self):
        mon_config = self._get_mon_config()
        p = self.profiles.get(
            mon_config.get("profile", DEFAULT_PROFILE),
            self.profiles.get(DEFAULT_PROFILE, {}),
        )
        p["merges"] = []
        self.on_layout_update(reposition=True)

    # [이해 포인트] 사용자가 캔버스에서 슬롯을 선택했을 때 실제 모니터 상의 해당 위치에 OSD(On-Screen Display) 형태의 오버레이 창을 잠깐 띄워 확인시켜줍니다.
    def _show_slot_overlay(self, index):
        if not self.tracker or index >= len(self.tracker.slot_rects):
            return

        rect = self.tracker.slot_rects[index]["rect"]
        overlay = tk.Toplevel(self.winfo_toplevel())
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True, "-alpha", 0.7)
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
        # [안전 장치] 1초(1000ms) 뒤에 자동으로 오버레이 창을 삭제하여 메모리 누수나 UI 멈춤을 방지합니다.
        self.after(1000, overlay.destroy)
