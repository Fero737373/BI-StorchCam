# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

RAINVIEWER_WEATHER_URL = "https://api.rainviewer.com/public/weather-maps.json"
RAINVIEWER_LEGACY_URL = "https://api.rainviewer.com/public/maps.json"
RAINVIEWER_HOST = "https://tilecache.rainviewer.com"
USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) BI-StorchCam/2.2"


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


def _short_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", exc)
        return str(reason)[:80]
    return str(exc)[:80]


def _fetch_json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", "replace")
        return json.loads(raw)


def _load_weather_maps() -> tuple[dict[str, Any] | None, str | None]:
    last_error: str | None = None
    for attempt in range(2):
        try:
            data = _fetch_json(RAINVIEWER_WEATHER_URL, timeout=10)
            if isinstance(data, dict):
                return data, None
            last_error = "Ungültige RainViewer-Antwort"
        except Exception as exc:
            last_error = _short_error(exc)
            if attempt == 0:
                time.sleep(0.5)
    return None, last_error


def _load_legacy_maps() -> tuple[list[int] | None, str | None]:
    try:
        data = _fetch_json(RAINVIEWER_LEGACY_URL, timeout=10)
        if isinstance(data, list):
            frames = sorted(int(x) for x in data if str(x).isdigit())
            return frames, None
        return None, "Ungültige Legacy-Antwort"
    except Exception as exc:
        return None, _short_error(exc)


def get_radar_metadata(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    loc = cfg.get("location", {}) if isinstance(cfg.get("location", {}), dict) else {}
    ui = cfg.get("ui", {}) if isinstance(cfg.get("ui", {}), dict) else {}
    radar_cfg = ui.get("radar", {}) if isinstance(ui.get("radar", {}), dict) else {}

    latitude = _to_float(loc.get("latitude"), 52.0302)
    longitude = _to_float(loc.get("longitude"), 8.5325)
    zoom = _to_int(radar_cfg.get("zoom"), 10)
    label = _clean_label(loc.get("label", "Bielefeld"))

    data, weather_error = _load_weather_maps()
    if data:
        radar = data.get("radar", {}) if isinstance(data, dict) else {}
        past_frames = radar.get("past", []) or []
        nowcast_frames = radar.get("nowcast", []) or []

        # Für einen öffentlichen Screen ist der letzte echte Messwert stabiler als
        # ein Nowcast-Frame. Nowcast bleibt nur Fallback, wenn RainViewer keine
        # Past-Frames liefert.
        frame = _latest_frame(past_frames) or _latest_frame(nowcast_frames)
        source = "past" if frame in past_frames else "nowcast"
        host = str(data.get("host") or RAINVIEWER_HOST).rstrip("/")

        if frame:
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

    # Fallback für Fälle, in denen /weather-maps.json auf dem Pi/CDN-Edge 502
    # liefert. Der ältere Endpunkt gibt Zeitstempel zurück und nutzt dasselbe
    # tilecache-Format.
    legacy_frames, legacy_error = _load_legacy_maps()
    if legacy_frames:
        timestamp = legacy_frames[-1]
        path = f"/v2/radar/{timestamp}"
        return {
            "ok": True,
            "host": RAINVIEWER_HOST,
            "frames": len(legacy_frames),
            "time": timestamp,
            "source": "legacy",
            "path": path,
            "tile_url": f"{RAINVIEWER_HOST}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
            "tile_size": 256,
            "label": label,
        }

    errors = " / ".join(x for x in [weather_error, legacy_error] if x)
    return {
        "ok": False,
        "error": errors or "RainViewer nicht erreichbar",
        "host": RAINVIEWER_HOST,
        "frames": 0,
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "label": label,
    }
