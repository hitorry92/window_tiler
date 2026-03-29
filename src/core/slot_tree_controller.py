import tkinter as tk
from src.gui.window_selector import WindowSelector

class SlotTreeController:
    """
    [역할] SettingsGUI에서 TreeView의 우클릭 메뉴 및 항목 상호작용 관련 컨트롤러 로직을 분리합니다.
    """
    def __init__(self, app_gui):
        self.app = app_gui
        self.root = app_gui.root

    def handle_right_click(self, event, slot_tree):
        sel = slot_tree.tree.selection()
        if not sel:
            return

        target_tracker, idx = slot_tree._get_target_tracker_and_slot(sel[0])
        if not target_tracker or idx == -1:
            return

        is_locked = target_tracker.slots[idx].get("locked", False)
        overlay_enabled = target_tracker.slots[idx].get("overlay_enabled", True)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="창 할당...",
            command=lambda: self.assign_window(target_tracker, idx),
        )
        menu.add_separator()
        menu.add_command(
            label="고정 해제" if is_locked else "고정",
            command=lambda: self.toggle_lock(target_tracker, idx),
        )
        menu.add_command(
            label="덮개 끄기" if overlay_enabled else "덮개 켜기",
            command=lambda: self.toggle_overlay(target_tracker, idx),
        )
        menu.add_command(
            label="창 할당 해제",
            command=lambda: self.unbind_slot(target_tracker, idx),
        )

        menu.post(event.x_root, event.y_root)

    def assign_window(self, target_tracker, idx):
        WindowSelector(self.root, target_tracker, self.app.update_ui, self.app.set_status, idx)

    def toggle_lock(self, target_tracker, idx):
        target_tracker.toggle_slot_lock(idx)
        locked = target_tracker.slots[idx].get("locked", False)
        self.app.set_status(
            f"● [M{target_tracker.monitor_index}] 슬롯 {idx} 고정됨"
            if locked
            else f"● [M{target_tracker.monitor_index}] 슬롯 {idx} 고정 해제됨",
            "info",
        )
        self.app.update_ui()

    def toggle_overlay(self, target_tracker, idx):
        target_tracker.toggle_overlay(idx)
        overlay_enabled = target_tracker.slots[idx].get("overlay_enabled", True)
        self.app.set_status(
            f"● [M{target_tracker.monitor_index}] 슬롯 {idx} 덮개 켜짐"
            if overlay_enabled
            else f"● [M{target_tracker.monitor_index}] 슬롯 {idx} 덮개 꺼짐",
            "info",
        )
        self.app.update_ui()

    def unbind_slot(self, target_tracker, idx):
        target_tracker.slots[idx]["hwnd"] = None
        target_tracker.reposition_all()
        self.app.update_ui()
        self.app.set_status(f"● [M{target_tracker.monitor_index}] 슬롯 {idx} 할당 해제됨", "info")
