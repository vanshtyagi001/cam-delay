"""
Configuration manager for CamDelay application.
Persists settings in JSON format in the user's AppData directory or local directory.
"""

import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "input_camera": "USB2.0 HD UVC WebCam",
    "input_camera_index": 0,
    "virtual_camera_name": "Asus Camera",
    "delay_ms": 200,
    "start_with_windows": False,
    "auto_start_camera": True,
    "resolution_width": 1280,
    "resolution_height": 720,
    "fps": 30.0
}

def get_config_dir() -> Path:
    """Returns application data directory: %APPDATA%/CamDelay."""
    appdata = os.getenv("APPDATA")
    if appdata:
        cfg_dir = Path(appdata) / "CamDelay"
    else:
        cfg_dir = Path.home() / ".camdelay"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir

def get_config_path() -> Path:
    return get_config_dir() / "config.json"

class Config:
    def __init__(self):
        self._path = get_config_path()
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value, auto_save=True):
        self._data[key] = value
        if auto_save:
            self.save()

    @property
    def input_camera(self) -> str:
        return self._data.get("input_camera", DEFAULT_CONFIG["input_camera"])

    @input_camera.setter
    def input_camera(self, val: str):
        self.set("input_camera", val)

    @property
    def input_camera_index(self) -> int:
        return self._data.get("input_camera_index", 0)

    @input_camera_index.setter
    def input_camera_index(self, val: int):
        self.set("input_camera_index", val)

    @property
    def virtual_camera_name(self) -> str:
        return self._data.get("virtual_camera_name", DEFAULT_CONFIG["virtual_camera_name"])

    @virtual_camera_name.setter
    def virtual_camera_name(self, val: str):
        self.set("virtual_camera_name", val)

    @property
    def delay_ms(self) -> int:
        return int(self._data.get("delay_ms", 200))

    @delay_ms.setter
    def delay_ms(self, val: int):
        self.set("delay_ms", int(val))

    @property
    def start_with_windows(self) -> bool:
        return bool(self._data.get("start_with_windows", False))

    @start_with_windows.setter
    def start_with_windows(self, val: bool):
        self.set("start_with_windows", bool(val))

    @property
    def auto_start_camera(self) -> bool:
        return bool(self._data.get("auto_start_camera", True))

    @auto_start_camera.setter
    def auto_start_camera(self, val: bool):
        self.set("auto_start_camera", bool(val))

    @property
    def resolution_width(self) -> int:
        return int(self._data.get("resolution_width", 1280))

    @property
    def resolution_height(self) -> int:
        return int(self._data.get("resolution_height", 720))

    @property
    def fps(self) -> float:
        return float(self._data.get("fps", 30.0))
