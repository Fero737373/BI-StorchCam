# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .defaults import DEFAULT_CONFIG


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
    """Move old Windows config location into the normal AppData path once."""
    if os.name != "nt" or CONFIG_PATH == LEGACY_CONFIG_PATH:
        return
    if CONFIG_PATH.exists() or not LEGACY_CONFIG_PATH.exists():
        return
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass


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
    return expand_user_values(deep_merge(DEFAULT_CONFIG, user_cfg))


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
