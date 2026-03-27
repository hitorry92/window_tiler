from . import win_utils
import pystray
from PIL import Image, ImageDraw
import threading


# [이해 포인트] 시스템 트레이 아이콘을 관리하고, 사용자 상호작용(메뉴 클릭)을 처리하는 클래스입니다.
class TrayManager:
    def __init__(self, on_pause_toggle, on_open_settings, on_quit):
        # [핵심 로직] 외부에서 전달받은 콜백 함수들을 저장하여, 트레이 메뉴 클릭 시 실행되도록 합니다.
        self.on_pause_toggle = on_pause_toggle
        self.on_open_settings = on_open_settings
        self.on_quit = on_quit
        self.icon = None
        self.is_paused = False

    def _create_image(self, color):
        # [이해 포인트] 트레이 아이콘에 표시될 이미지를 동적으로 생성하는 함수입니다.
        width, height = 64, 64
        # 투명 배경(RGBA)으로 변경하여 시인성 개선
        # [안전 장치] 투명 배경을 사용하여 다양한 윈도우 테마(밝은/어두운 모드)에서도 아이콘이 잘 보이게 합니다.
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # 아이콘 배경 원 (흰색 테두리)
        dc.ellipse([4, 4, 60, 60], fill="white")
        # 상태 표시 원
        # [핵심 로직] 전달받은 color 값(green 또는 gray)으로 원을 채워 현재 상태(실행 중/일시정지)를 시각적으로 나타냅니다.
        dc.ellipse([12, 12, 52, 52], fill=color)
        return image

    def start(self):
        # [핵심 로직] 트레이 아이콘에서 우클릭했을 때 나타날 메뉴 항목들을 정의합니다.
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
        # [위험] 트레이 아이콘 실행(run)은 블로킹(blocking) 호출이므로, 메인 스레드가 멈추지 않도록 별도의 백그라운드 데몬 스레드에서 실행해야 합니다.
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _toggle_pause(self, icon=None, item=None):
        # [핵심 로직] 일시정지 상태를 반전시키고, 그에 맞춰 아이콘의 색상과 툴팁 텍스트를 업데이트합니다.
        self.is_paused = not self.is_paused
        status_text = "일시정지" if self.is_paused else "실행 중"
        color = "gray" if self.is_paused else "green"

        self.icon.icon = self._create_image(color)
        self.icon.title = f"Window Tiler - {status_text}"

        # 외부 콜백 호출
        # [이해 포인트] 상태 변경이 완료되면 메인 프로그램에도 이 사실을 알려서 실제 동작을 제어하도록 합니다.
        self.on_pause_toggle(self.is_paused)

    def set_paused_state(self, paused):
        """외부에서 상태를 강제로 변경할 때 사용 (예: 최소화 시)"""
        # [안전 장치] 트레이 메뉴뿐만 아니라 외부 단축키나 프로그램 내부 로직에 의해 상태가 변할 때 아이콘도 동기화되도록 합니다.
        self.is_paused = paused
        color = "gray" if paused else "green"
        if self.icon:
            self.icon.icon = self._create_image(color)
            status_text = "일시정지" if paused else "실행 중"
            self.icon.title = f"Window Tiler - {status_text}"

    def stop(self):
        # [위험] 프로그램 종료 시 트레이 아이콘이 시스템 트레이에 남아있는 버그(고스트 아이콘)를 방지하기 위해 명시적으로 stop()을 호출해야 합니다.
        if self.icon:
            self.icon.stop()
