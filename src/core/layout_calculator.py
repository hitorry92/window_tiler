from typing import List, Dict, Any, Tuple

class LayoutCalculator:
    @staticmethod
    def calculate_slots(x: int, y: int, w: int, h: int, h_splits: List[float], v_splits: List[float], merges: List[List[int]] = None, gap: int = 0) -> List[Dict[str, Any]]:
        """수직/수평 분할 비율 리스트를 받아 실제 픽셀 좌표(사각형)로 변환하는 알고리즘"""
        # 양 끝점(0.0과 1.0)을 포함하여 쪼갤 기준선을 만듭니다.
        h_points = [0.0] + sorted(h_splits) + [1.0]
        v_points = [0.0] + sorted(v_splits) + [1.0]

        base_slots = []
        # 그리드 기반으로 베이스 슬롯 생성
        for i in range(len(h_points) - 1):
            for j in range(len(v_points) - 1):
                sx = int(x + v_points[j] * w)
                sy = int(y + h_points[i] * h)
                sw = int((v_points[j + 1] - v_points[j]) * w)
                sh = int((h_points[i + 1] - h_points[i]) * h)

                # 사용자 설정 여백(gap) 적용. 최소 1픽셀은 보장.
                rect = (sx + gap, sy + gap, max(1, sw - 2 * gap), max(1, sh - 2 * gap))
                base_slots.append({"rect": rect, "base_indices": [len(base_slots)]})

        if not merges:
            return base_slots

        # [로직] 슬롯 병합 처리 (사용자가 우클릭으로 칸을 합친 경우)
        merged_map = {}
        for i, group in enumerate(merges):
            for idx in group:
                merged_map[idx] = i  # 이 인덱스의 슬롯은 i번째 그룹에 속함

        final_slots = []
        groups_added = set()

        for idx in range(len(base_slots)):
            if idx in merged_map:
                gid = merged_map[idx]
                if gid not in groups_added:
                    # 그룹 전체를 아우르는 거대한 사각형(Bounding Box)을 계산합니다.
                    group = merges[gid]
                    gx = min(
                        base_slots[i]["rect"][0] for i in group if i < len(base_slots)
                    )
                    gy = min(
                        base_slots[i]["rect"][1] for i in group if i < len(base_slots)
                    )
                    g_right = max(
                        base_slots[i]["rect"][0] + base_slots[i]["rect"][2] + gap
                        for i in group
                        if i < len(base_slots)
                    )
                    g_bottom = max(
                        base_slots[i]["rect"][1] + base_slots[i]["rect"][3] + gap
                        for i in group
                        if i < len(base_slots)
                    )

                    final_slots.append(
                        {
                            "rect": (gx, gy, g_right - gx, g_bottom - gy),
                            "base_indices": list(group),
                        }
                    )
                    groups_added.add(gid)
            else:
                final_slots.append(base_slots[idx])

        return final_slots
