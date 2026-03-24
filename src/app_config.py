import json
import os

CONFIG_FILE = "config.json"
PROFILES_FILE = "profiles.json"

DEFAULT_CONFIG = {
    "profile": "기본",
    "main_slot_index": 0,
    "delay": 0.3,
    "poll_interval": 0.1,
    "monitor_index": 0,
    "hotkey": "Ctrl+Shift+T",
    "gap": 0,
    "excluded_windows": [],
}

DEFAULT_PROFILES = {
    "기본": {"horizontal": [], "vertical": [0.5], "merges": [], "main_slot_index": 0}
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 마이그레이션: 구버전 필드명 처리
            if "current_profile" in config and "profile" not in config:
                config["profile"] = config["current_profile"]

            # 멀티 모니터 설정이 있다면 현재 인덱스 기준으로 추출
            if "monitor_configs" in config:
                mon_idx = str(config.get("monitor_index", 0))
                if mon_idx in config["monitor_configs"]:
                    mon_cfg = config["monitor_configs"][mon_idx]
                    if "profile" not in config:
                        config["profile"] = mon_cfg.get("profile", "기본")
                    if "main_slot_index" not in config:
                        config["main_slot_index"] = mon_cfg.get("main_slot_index", 0)

            # 누락된 필수 필드 채우기
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def load_profiles():
    profiles = DEFAULT_PROFILES.copy()
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 읽어온 데이터로 업데이트하되, 필수 기본값이 없다면 유지됨 (Cycle 15)
                profiles.update(loaded)
        except Exception:
            pass
    return profiles


def save_profiles(profiles):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)
