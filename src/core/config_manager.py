import json
import os
from typing import Dict, Any, Optional
from src.app_config import (
    DEFAULT_CONFIG, 
    DEFAULT_PROFILES, 
    CONFIG_FILE, 
    PROFILES_FILE,
    DEFAULT_PROFILE
)

class ConfigManager:
    """
    [역할] 애플리케이션의 설정(Config)과 프로필(Profiles)의 로드 및 저장을 전담하는 클래스입니다.
    """
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.profiles: Dict[str, Any] = {}
        
    def load_all(self):
        self.config = self.load_config()
        self.profiles = self.load_profiles()

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                    if "current_profile" in config and "profile" not in config:
                        config["profile"] = config["current_profile"]

                    if "monitor_configs" in config:
                        mon_idx = str(config.get("monitor_index", 0))
                        if mon_idx in config["monitor_configs"]:
                            mon_cfg = config["monitor_configs"][mon_idx]
                            if "profile" not in config:
                                config["profile"] = mon_cfg.get("profile", DEFAULT_PROFILE)
                            if "main_slot_index" not in config:
                                config["main_slot_index"] = mon_cfg.get("main_slot_index", 0)

                    for k, v in DEFAULT_CONFIG.items():
                        if k not in config:
                            config[k] = v
                    if "monitor_configs" not in config:
                        config["monitor_configs"] = {}
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")

        config = DEFAULT_CONFIG.copy()
        config["monitor_configs"] = {}
        return config

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        if config is not None:
            self.config = config
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def load_profiles(self) -> Dict[str, Any]:
        profiles = DEFAULT_PROFILES.copy()
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if k not in profiles:
                            profiles[k] = {"horizontal": [], "vertical": [0.5], "merges": [], "main_slot_index": 0}
                        if isinstance(v, dict):
                            profiles[k].update(v)
            except Exception as e:
                print(f"Error loading profiles: {e}")
        return profiles

    def save_profiles(self, profiles: Optional[Dict[str, Any]] = None) -> None:
        if profiles is not None:
            self.profiles = profiles
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_value(config: Dict[str, Any], key: str, default: Any) -> Any:
        if config is None:
            return default
        return config.get(key, default)
