from typing import Dict, List, Any, Set

class GlobalWindowManager:
    """
    [역할] 여러 모니터(WindowTracker) 간의 상호작용 및 글로벌 스왑, 자동 채우기 등
    전역적인(Global) 윈도우 배정 로직을 전담하는 클래스입니다.
    """
    def __init__(self, app_instance):
        self.app = app_instance
        self.config = app_instance.config
        self.trackers = app_instance.trackers

    def auto_fill(self, excluded_windows: List[int] = None, is_specific_targets: bool = False) -> int:
        """[핵심 로직] 글로벌 스왑 모드일 때 전체 모니터를 대상으로 자동 지정을 수행합니다."""
        import win32gui
        from src.win_utils import get_window_list, is_own_window

        if is_specific_targets:
            targets = excluded_windows if excluded_windows else []
        else:
            if excluded_windows is None:
                excluded_windows = []
            windows = get_window_list(None)
            my_hwnd = self.app.gui.root.winfo_id() if self.app.gui and self.app.gui.root else 0
            targets = [
                w[0]
                for w in windows
                if w[0] != my_hwnd
                and not is_own_window(w[1])
                and w[1] not in excluded_windows
            ]

        if not targets:
            return 0

        g_mon = self.config.get("global_main_monitor", 0)
        g_slot = self.config.get("global_main_slot", 0)

        locks = [self.trackers[i].lock for i in sorted(self.trackers.keys())]
        for lock in locks:
            lock.acquire()

        try:
            for tracker in self.trackers.values():
                for s in tracker.slots:
                    if not s.get("locked", False):
                        s["hwnd"] = None

            fill_queue = []
            tracker_main = self.trackers.get(g_mon)

            # 1순위: 글로벌 메인 슬롯
            if tracker_main and g_slot < len(tracker_main.slots):
                fill_queue.append((tracker_main, g_slot))

            # 2순위: 글로벌 메인 모니터의 나머지 슬롯들 (오름차순)
            if tracker_main:
                for i in range(len(tracker_main.slots)):
                    if i != g_slot:
                        fill_queue.append((tracker_main, i))

            # 3순위: 나머지 모니터들의 슬롯들을 모니터 번호 오름차순, 슬롯 번호 오름차순으로 채움 (로컬 메인 무시)
            for mon_idx in sorted(self.trackers.keys()):
                if mon_idx != g_mon:
                    tracker = self.trackers[mon_idx]
                    for i in range(len(tracker.slots)):
                        fill_queue.append((tracker, i))

            count = 0
            # 사용 가능한 창 목록 복사
            available_targets = list(targets)

            # 현재 모든 슬롯에 배정된 창 HWND 수집 (고정 여부와 관계없이)
            assigned_hwnds = set()
            for tracker in self.trackers.values():
                for s in tracker.slots:
                    if s.get("hwnd"):
                        assigned_hwnds.add(s["hwnd"])
            # 이미 배정된 창은 제외 (중복 배정 방지) - targets는 HWND 리스트
            available_targets = [
                w for w in available_targets if w not in assigned_hwnds
            ]

            for tracker, slot_idx in fill_queue:
                if not available_targets:
                    break
                if not tracker.slots[slot_idx].get("locked", False):
                    # 할당할 창을 목록에서 pop
                    hwnd_to_assign = available_targets.pop(0)
                    tracker.slots[slot_idx]["hwnd"] = hwnd_to_assign
                    count += 1

            for tracker in self.trackers.values():
                tracker.reposition_all()

            return count

        finally:
            for lock in reversed(locks):
                lock.release()

    def handle_global_swap(self, monitor_idx: int, slot_idx: int):
        """[핵심 로직] 오버레이를 클릭했거나 포커스 변경시 글로벌 스왑을 처리하는 로직"""
        from src.app_config import DEFAULT_SWAP_MODE
        swap_mode = self.config.get("swap_mode", DEFAULT_SWAP_MODE)

        if swap_mode == "global":
            g_mon = self.config.get("global_main_monitor", 0)
            g_slot = self.config.get("global_main_slot", 0)

            # 자기 자신이 글로벌 메인 슬롯이면 무시
            if monitor_idx == g_mon and slot_idx == g_slot:
                return

            tracker_src = self.trackers.get(monitor_idx)
            tracker_dst = self.trackers.get(g_mon)

            if not tracker_src or not tracker_dst:
                return

            # [버그 수정] 같은 모니터 내에서의 글로벌 메인 스왑인 경우, 락을 두 번 얻으려고 하면(Reentrant Lock이 아닐 때) 데드락 발생.
            if monitor_idx == g_mon:
                with tracker_src.lock:
                    slot_src = tracker_src.slots[slot_idx]
                    slot_dst = tracker_src.slots[g_slot]

                    if slot_src.get("locked") or slot_dst.get("locked"):
                        return

                    # 스왑 처리
                    tracker_src.slots[slot_idx], tracker_src.slots[g_slot] = (
                        slot_dst,
                        slot_src,
                    )
                tracker_src.reposition_all()
                self.app._request_ui_update()
            else:
                # [안전 장치] 데드락(Deadlock) 방지를 위해 항상 인덱스가 작은 모니터부터 락(Lock)을 획득합니다.
                t1, t2 = (
                    (tracker_src, tracker_dst)
                    if monitor_idx < g_mon
                    else (tracker_dst, tracker_src)
                )

                with t1.lock:
                    with t2.lock:
                        slot_src = tracker_src.slots[slot_idx]
                        slot_dst = tracker_dst.slots[g_slot]

                        if slot_src.get("locked") or slot_dst.get("locked"):
                            return

                        # 스왑 처리
                        tracker_src.slots[slot_idx], tracker_dst.slots[g_slot] = (
                            slot_dst,
                            slot_src,
                        )

                tracker_src.reposition_all()
                tracker_dst.reposition_all()
                self.app._request_ui_update()

        else:
            # 로컬 스왑 (기존 동작)
            tracker = self.trackers.get(monitor_idx)
            if tracker:
                tracker.swap_to_main(slot_idx)
