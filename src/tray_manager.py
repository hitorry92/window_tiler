from . import win_utils
import pystray
from PIL import Image, ImageDraw
import threading


class TrayManager:
    def __init__(self, on_pause_toggle, on_open_settings, on_quit):
        self.on_pause_toggle = on_pause_toggle
        self.on_open_settings = on_open_settings
        self.on_quit = on_quit
        self.icon = None
        self.is_paused = False

    def _create_image(self, color):
        width, height = 64, 64
        # 투명 배경(RGBA)으로 변경하여 시인성 개선
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # 아이콘 배경 원 (흰색 테두리)
        dc.ellipse([4, 4, 60, 60], fill="white")
        # 상태 표시 원
        dc.ellipse([12, 12, 52, 52], fill=color)
        return image

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                "상태: 실행 중",
                lambda: None,
                enabled=False,
                visible=lambda item: not self.is_paused,
            ),
            pystray.MenuItem(
                "상태: 일시정지",
                lambda: None,
                enabled=False,
                visible=lambda item: self.is_paused,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("일시정지/재개", self._toggle_pause),
            pystray.MenuItem("설정", self.on_open_settings, default=True),
            pystray.MenuItem("종료", self.on_quit),
        )

        self.icon = pystray.Icon(
            "WindowTiler", self._create_image("green"), "Window Tiler", menu
        )
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _toggle_pause(self, icon=None, item=None):
        self.is_paused = not self.is_paused
        status_text = "일시정지" if self.is_paused else "실행 중"
        color = "gray" if self.is_paused else "green"

        self.icon.icon = self._create_image(color)
        self.icon.title = f"Window Tiler - {status_text}"

        # 외부 콜백 호출
        self.on_pause_toggle(self.is_paused)

    def set_paused_state(self, paused):
        """외부에서 상태를 강제로 변경할 때 사용 (예: 최소화 시)"""
        self.is_paused = paused
        color = "gray" if paused else "green"
        if self.icon:
            self.icon.icon = self._create_image(color)
            status_text = "일시정지" if paused else "실행 중"
            self.icon.title = f"Window Tiler - {status_text}"

    def stop(self):
        if self.icon:
            self.icon.stop()
