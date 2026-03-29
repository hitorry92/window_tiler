from typing import List, Dict, Any, Optional
import win32gui

class SlotManager:
    """
    [역할] 윈도우 창(HWND)들의 슬롯 배정, 잠금, 해제 등의 상태 관리를 담당합니다.
    """
    def __init__(self, num_slots: int):
        self.slots = [{"hwnd": None, "locked": False, "overlay_enabled": True} for _ in range(num_slots)]

    def resize(self, num_slots: int):
        while len(self.slots) < num_slots:
            self.slots.append({"hwnd": None, "locked": False, "overlay_enabled": True})
        self.slots = self.slots[:num_slots]

    def swap(self, idx1: int, idx2: int) -> bool:
        if idx1 < 0 or idx2 < 0 or idx1 >= len(self.slots) or idx2 >= len(self.slots):
            return False
            
        slot1 = self.slots[idx1]
        slot2 = self.slots[idx2]

        if slot1.get("locked") or slot2.get("locked"):
            return False
        if not slot1.get("overlay_enabled", True) or not slot2.get("overlay_enabled", True):
            return False

        self.slots[idx1], self.slots[idx2] = slot2, slot1
        return True

    def toggle_lock(self, index: int) -> bool:
        if 0 <= index < len(self.slots):
            self.slots[index]["locked"] = not self.slots[index].get("locked", False)
            return True
        return False

    def toggle_overlay(self, index: int) -> bool:
        if 0 <= index < len(self.slots):
            current = self.slots[index].get("overlay_enabled", True)
            self.slots[index]["overlay_enabled"] = not current
            return not current
        return False

    def clear_invalid_hwnds(self) -> bool:
        """존재하지 않는 창을 슬롯에서 제거하고 상태가 변경되었는지 반환합니다."""
        changed = False
        for i, slot in enumerate(list(self.slots)):
            if slot["hwnd"] and not win32gui.IsWindow(slot["hwnd"]):
                if not slot.get("locked"):
                    self.slots[i] = {
                        "hwnd": None,
                        "locked": False,
                        "overlay_enabled": slot.get("overlay_enabled", True),
                    }
                else:
                    self.slots[i]["hwnd"] = None
                changed = True
        return changed

    def is_hwnd_assigned(self, hwnd: int) -> bool:
        return any(s["hwnd"] == hwnd for s in self.slots)

    def get_slot_index_by_hwnd(self, hwnd: int) -> int:
        for i, s in enumerate(self.slots):
            if s["hwnd"] == hwnd:
                return i
        return -1

    def clear_unlocked_slots(self):
        """고정되지 않은 모든 슬롯의 창을 비웁니다."""
        for s in self.slots:
            if not s.get("locked", False):
                s["hwnd"] = None

    def get_assigned_hwnds(self) -> set:
        """현재 할당된 모든 창의 핸들을 반환합니다."""
        return {s["hwnd"] for s in self.slots if s.get("hwnd")}
