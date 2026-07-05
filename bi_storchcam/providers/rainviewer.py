# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import urllib.request
from typing import Any

RAINVIEWER_URL = "https://api.rainviewer.com/public/weather-maps.json"


def _to_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _latest_frame(frames: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [frame for frame in frames if isinstance(frame, dict) and frame.get("path")]
    if not valid:
        return None
    return max(valid, key=lambda frame: int(frame.get("time") or 0))


def get_radar_metadata(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    loc = cfg.get("location", {}) if isinstance(cfg.get("location", {}), dict) else {}
    ui = cfg.get("ui", {}) if isinstance(cfg.get("ui", {}), dict) else {}
    radar_cfg = ui.get("radar", {}) if isinstance(ui.get("radar", {}), dict) else {}

    latitude = _to_float(loc.get("latitude"), 52.0302)
    longitude = _to_float(loc.get("longitude"), 8.5325)
    zoom = _to_int(radar_cfg.get("zoom"), 10)

    req = urllib.request.Request(RAINVIEWER_URL, headers={"User-Agent": "BI-StorchCam/2.1"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "frames": 0,
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
        }

    radar = data.get("radar", {}) if isinstance(data, dict) else {}
    frames: list[dict[str, Any]] = []
    frames.extend(radar.get("past", []) or [])
    frames.extend(radar.get("nowcast", []) or [])

    frame = _latest_frame(frames)
    host = str(data.get("host") or "https://tilecache.rainviewer.com").rstrip("/")
    if not frame:
        return {
            "ok": False,
            "error": "Keine Radar-Frames von RainViewer erhalten.",
            "host": host,
            "frames": 0,
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
        }

    path = str(frame.get("path", ""))
    return {
        "ok": True,
        "host": host,
        "frames": len(frames),
        "time": frame.get("time"),
        "path": path,
        "tile_url": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "tile_size": 256,
    }
