import json
import os

# [핵심 로직] 프로그램 설정 및 프로필을 저장할 파일명 정의
CONFIG_FILE = "config.json"
PROFILES_FILE = "profiles.json"

# [이해 포인트] 프로그램이 처음 실행되거나 설정 파일이 없을 때 사용할 기본 설정값 (단축키, 딜레이 등)
DEFAULT_CONFIG = {
    "profile": "기본",
    "main_slot_index": 0,
    "delay": 0.3,
    "poll_interval": 0.1,
    "monitor_index": 0,
    "hotkey": "Ctrl+Shift+E",
    "gap": 0,
    "excluded_windows": [],
}

# [이해 포인트] 창 배치 분할 비율이나 위치 정보를 담고 있는 초기 프로필 데이터
DEFAULT_PROFILES = {
    "기본": {"horizontal": [], "vertical": [0.5], "merges": [], "main_slot_index": 0}
}


def load_config():
    # [안전 장치] 설정 파일이 실제로 존재하는지 먼저 확인하여 오류 방지
    if os.path.exists(CONFIG_FILE):
        # [위험] 파일을 읽을 때 권한 문제나 파일 손상이 있을 수 있으므로 주의 필요
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 마이그레이션: 구버전 필드명 처리
            # [이해 포인트] 이전 버전의 설정 파일과 호환되도록 필드명을 최신 구조로 변경해주는 과정
            if "current_profile" in config and "profile" not in config:
                config["profile"] = config["current_profile"]

            # 멀티 모니터 설정이 있다면 현재 인덱스 기준으로 추출
            # [핵심 로직] 다중 모니터 환경에서 사용 중인 모니터(monitor_index)에 해당하는 설정만을 추출
            if "monitor_configs" in config:
                mon_idx = str(config.get("monitor_index", 0))
                if mon_idx in config["monitor_configs"]:
                    mon_cfg = config["monitor_configs"][mon_idx]
                    if "profile" not in config:
                        config["profile"] = mon_cfg.get("profile", "기본")
                    if "main_slot_index" not in config:
                        config["main_slot_index"] = mon_cfg.get("main_slot_index", 0)

            # 누락된 필수 필드 채우기
            # [안전 장치] 설정 파일에 일부 키가 지워졌거나 없어도, 기본 설정(DEFAULT_CONFIG)으로 안전하게 채움
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            if "monitor_configs" not in config:
                config["monitor_configs"] = {}
            return config

    # [이해 포인트] 파일이 아예 없다면 기본 설정값의 복사본을 반환하여 사용
    config = DEFAULT_CONFIG.copy()
    config["monitor_configs"] = {}
    return config


def save_config(config):
    # [핵심 로직] 현재 설정 딕셔너리를 지정된 JSON 파일로 저장하는 함수
    # [위험] 저장하는 도중에 프로그램이 강제로 종료되면 파일 내용이 빈 상태로 손상될 수 있음
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        # [이해 포인트] ensure_ascii=False 옵션을 주어 한글 값들이 깨지지 않고 온전히 저장되도록 설정
        json.dump(config, f, indent=4, ensure_ascii=False)


def load_profiles():
    # [이해 포인트] 데이터 유실을 막기 위해 우선 기본 프로필 데이터 복사본을 만들어둠
    profiles = DEFAULT_PROFILES.copy()
    if os.path.exists(PROFILES_FILE):
        # [안전 장치] 파일 읽기 실패나 JSON 형식이 잘못되었을 때 프로그램 종료를 막기 위한 try-except 구문
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 읽어온 데이터로 업데이트하되, 필수 기본값이 없다면 유지됨 (Cycle 15)
                # [핵심 로직] 성공적으로 읽어온 프로필 데이터로 기존 딕셔너리 정보 업데이트
                profiles.update(loaded)
        except Exception:
            # [위험] 에러 발생 시 그냥 넘어가므로 사용자 입장에서는 왜 프로필이 초기화되었는지 알 수 없음
            pass
    return profiles


def save_profiles(profiles):
    # [핵심 로직] 사용자가 수정한 창 배치 프로필 데이터를 JSON 파일로 저장
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)
