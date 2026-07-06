# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .defaults import DEFAULT_CONFIG

CONFIG_SCHEMA_VERSION = 3


def _platform_app_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "BI-StorchCam"
        return Path.home() / "AppData" / "Roaming" / "BI-StorchCam"
    return Path.home() / ".config" / "BI-StorchCam"


APP_DIR = _platform_app_dir()
CONFIG_PATH = APP_DIR / "config.json"
LEGACY_CONFIG_PATH = Path.home() / ".config" / "BI-StorchCam" / "config.json"


def _migrate_legacy_windows_config() -> None:
    if os.name != "nt" or CONFIG_PATH == LEGACY_CONFIG_PATH:
        return
    if CONFIG_PATH.exists() or not LEGACY_CONFIG_PATH.exists():
        return
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass


def _release_int(value: Any, fallback: int, minimum: int, maximum: int) -> int:
    try:
        num = int(value)
    except Exception:
        return fallback
    if num < minimum or num > maximum:
        return fallback
    return num


def _release_float(value: Any, fallback: float, minimum: float, maximum: float) -> float:
    try:
        num = float(value)
    except Exception:
        return fallback
    if num < minimum or num > maximum:
        return fallback
    return num


def _is_placeholder_stop(stop: Any) -> bool:
    if not isinstance(stop, dict):
        return False
    title = str(stop.get("title") or "").strip().upper()
    station = str(stop.get("station_name") or "").strip().lower()
    return title == "BEISPIEL" or "gellershagen schneiderstraße" in station


def migrate_config(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    cfg = copy.deepcopy(config)
    changed = False

    app = cfg.setdefault("app", {})
    old_version = int(app.get("config_schema_version", 0) or 0)

    ui = cfg.setdefault("ui", {})
    radar = ui.setdefault("radar", {})

    if old_version < 3:
        values = {
            "height": _release_int(radar.get("height", 180), 320, 220, 520),
            "width": _release_int(radar.get("width", 260), 420, 300, 560),
            "zoom": _release_int(radar.get("zoom", 10), 12, 8, 14),
            "opacity": _release_float(radar.get("opacity", 0.82), 0.92, 0.4, 1.0),
        }
        for key, value in values.items():
            if radar.get(key) != value:
                radar[key] = value
                changed = True

        if ui.get("theme") != "production":
            ui["theme"] = "production"
            changed = True

        system = ui.setdefault("system", {})
        if system.get("enabled", False):
            system["enabled"] = False
            changed = True
        if system.get("diagnostic_only") is not True:
            system["diagnostic_only"] = True
            changed = True

        transit_ui = ui.setdefault("transit", {})
        transit = cfg.setdefault("transit", {})
        stops = transit.get("stops", [])
        if isinstance(stops, list):
            cleaned_stops = [stop for stop in stops if not _is_placeholder_stop(stop)]
            if cleaned_stops != stops:
                transit["stops"] = cleaned_stops
                changed = True
            if not cleaned_stops and transit_ui.get("enabled", False):
                transit_ui["enabled"] = False
                changed = True

    if app.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        app["config_schema_version"] = CONFIG_SCHEMA_VERSION
        changed = True

    return cfg, changed


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def expand_user_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: expand_user_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_user_values(v) for v in value]
    if isinstance(value, str) and value.startswith("~/"):
        return os.path.expanduser(value)
    return value


def load_config(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        _migrate_legacy_windows_config()
    cfg_path = path or CONFIG_PATH
    if not cfg_path.exists():
        save_config(DEFAULT_CONFIG, cfg_path)
    try:
        user_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        user_cfg = {}

    merged = deep_merge(DEFAULT_CONFIG, user_cfg)
    migrated, changed = migrate_config(merged)
    if changed:
        save_config(migrated, cfg_path)
    return expand_user_values(migrated)


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    cfg_path = path or CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def config_path() -> Path:
    _migrate_legacy_windows_config()
    APP_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_PATH


def cache_dir(config: dict[str, Any]) -> Path:
    raw = config.get("app", {}).get("cache_dir", "~/.cache/BI-StorchCam")
    p = Path(os.path.expanduser(str(raw)))
    p.mkdir(parents=True, exist_ok=True)
    return p
