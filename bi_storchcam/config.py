from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

APP_DIR_NAME = "BI-StorchCam"
DEFAULT_STREAM_URL = "https://www.youtube.com/watch?v=mRECZ-PJ2So"

DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "BI-StorchCam",
        "language": "de",
    },
    "video": {
        "url": DEFAULT_STREAM_URL,
        "fullscreen": True,
    },
    "location": {
        "query": "Bielefeld",
        "label": "Bielefeld",
        "latitude": 52.0302,
        "longitude": 8.5325,
    },
    "transit": {
        "provider": "vrr",
        "station_id": "23005489",
        "station_name": "Gellershagen Schneiderstraße",
        "refresh_seconds": 15,
        "max_rows": 5,
    },
    "weather": {
        "refresh_seconds": 300,
    },
    "ui": {
        "opacity_top": 0.82,
        "opacity_weather": 0.78,
        "opacity_bus": 0.88,
        "top_clock_font_size": 34,
        "weather_font_size": 15,
        "bus_font_size": 12,
        "bus_header_font_size": 14,
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def config_dir() -> Path:
    system = platform.system().lower()
    if system == "windows":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / APP_DIR_NAME
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def default_config_path() -> Path:
    return config_dir() / "config.json"


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or default_config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_CONFIG)

    return deep_merge(DEFAULT_CONFIG, data)


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> Path:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def config_exists(path: Optional[Path] = None) -> bool:
    return (path or default_config_path()).exists()
