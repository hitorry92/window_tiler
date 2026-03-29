from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int
    
    @property
    def tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

@dataclass
class SlotState:
    hwnd: Optional[int] = None
    locked: bool = False
    overlay_enabled: bool = True

@dataclass
class MonitorInfo:
    handle: Any
    rect: Tuple[int, int, int, int]
    work: Tuple[int, int, int, int]
    name: str
    width: int
    height: int
    x: int
    y: int
