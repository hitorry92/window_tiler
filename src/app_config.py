import json
import os

# [핵심 상수] 프로그램 정보
APP_NAME = "Window Tiler"

# [핵심 상수] 기본값
DEFAULT_PROFILE = "기본"
DEFAULT_SWAP_MODE = "local"
DEFAULT_DELAY = 0.3
DEFAULT_POLL_INTERVAL = 0.1

# [핵심 상수] DPI 관련
DEFAULT_DPI_SCALE = 1.0
PREVIEW_MARGIN_RATIO = 0.95
BASE_DPI = 96.0


def get_config_value(config, key, default):
    """안전한 설정 값 조회 (None 안전)"""
    if config is None:
        return default
    return config.get(key, default)


# [핵심 로직] 프로그램 설정 및 프로필을 저장할 파일명 정의
CONFIG_FILE = "config.json"
PROFILES_FILE = "profiles.json"

# [이해 포인트] 프로그램이 처음 실행되거나 설정 파일이 없을 때 사용할 기본 설정값 (단축키, 딜레이 등)
DEFAULT_CONFIG = {
    "profile": DEFAULT_PROFILE,
    "main_slot_index": 0,
    "delay": DEFAULT_DELAY,
    "poll_interval": DEFAULT_POLL_INTERVAL,
    "monitor_index": 0,
    "hotkey": "Ctrl+Shift+E",
    "gap": 0,
    "excluded_windows": [],
}

# [이해 포인트] 창 배치 분할 비율이나 위치 정보를 담고 있는 초기 프로필 데이터
DEFAULT_PROFILES = {
    DEFAULT_PROFILE: {
        "horizontal": [],
        "vertical": [0.5],
        "merges": [],
        "main_slot_index": 0,
    }
}


def load_config():
    from .core.config_manager import ConfigManager

    return ConfigManager().load_config()


def save_config(config):
    from .core.config_manager import ConfigManager

    ConfigManager().save_config(config)


def load_profiles():
    from .core.config_manager import ConfigManager

    return ConfigManager().load_profiles()


def save_profiles(profiles):
    from .core.config_manager import ConfigManager

    ConfigManager().save_profiles(profiles)
