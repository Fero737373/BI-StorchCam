# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
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


def _clean_label(label: Any) -> str:
    label = re.sub(r"\s+", " ", str(label or "Bielefeld")).strip()
    parts = [p.strip() for p in label.split(",") if p.strip()]
    if len(parts) >= 4:
        return parts[3]
    if len(label) > 24:
        return label[:21].rstrip() + "…"
    return label or "Bielefeld"


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
    label = _clean_label(loc.get("label", "Bielefeld"))

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
            "label": label,
        }

    radar = data.get("radar", {}) if isinstance(data, dict) else {}
    past_frames = radar.get("past", []) or []
    nowcast_frames = radar.get("nowcast", []) or []

    # Für einen öffentlichen Screen ist der letzte echte Messwert stabiler als
    # ein Nowcast-Frame. Nowcast bleibt nur Fallback, wenn RainViewer keine
    # Past-Frames liefert.
    frame = _latest_frame(past_frames) or _latest_frame(nowcast_frames)
    source = "past" if frame in past_frames else "nowcast"
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
            "label": label,
        }

    path = str(frame.get("path", ""))
    return {
        "ok": True,
        "host": host,
        "frames": len(past_frames) + len(nowcast_frames),
        "time": frame.get("time"),
        "source": source,
        "path": path,
        "tile_url": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "tile_size": 256,
        "label": label,
    }
