"""RainViewer radar metadata provider with measured/nowcast/legacy states."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from ..version import __version__

LOGGER = logging.getLogger(__name__)
WEATHER_URL = "https://api.rainviewer.com/public/weather-maps.json"
LEGACY_URL = "https://api.rainviewer.com/public/maps.json"
DEFAULT_HOST = "https://tilecache.rainviewer.com"
ATTRIBUTION = "RainViewer · OpenStreetMap-Mitwirkende"


def _fetch_json(url: str, timeout: int = 10) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"BI-StorchCam/{__version__}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _short_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return str(getattr(exc, "reason", exc))[:120]
    return str(exc)[:120]


def _latest(frames: Any) -> dict[str, Any] | None:
    if not isinstance(frames, list):
        return None
    usable = [frame for frame in frames if isinstance(frame, dict) and frame.get("path")]
    return max(usable, key=lambda frame: int(frame.get("time") or 0), default=None)


def _label(value: Any) -> str:
    clean = re.sub(r"\s+", " ", str(value or "Bielefeld")).strip()
    return (clean.split(",", 1)[0] or "Bielefeld")[:64]


def _base(config: dict[str, Any]) -> dict[str, Any]:
    location = config.get("location", {})
    radar_ui = config.get("ui", {}).get("radar", {})
    return {
        "provider": "rainviewer",
        "host": DEFAULT_HOST,
        "latitude": float(location.get("latitude", 52.0302)),
        "longitude": float(location.get("longitude", 8.5325)),
        "zoom": int(radar_ui.get("zoom", 12)),
        "label": _label(location.get("label")),
        "tile_size": 256,
        "attribution": ATTRIBUTION,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _result(base: dict[str, Any], timestamp: int, path: str, host: str, source: str, frames: int) -> dict[str, Any]:
    data_time = datetime.fromtimestamp(timestamp, timezone.utc)
    age_minutes = max(0, int((datetime.now(timezone.utc) - data_time).total_seconds() // 60))
    labels = {"measurement": "Messwert", "nowcast": "Nowcast", "legacy": "Legacy-Fallback"}
    return {
        **base,
        "ok": True,
        "offline": False,
        "host": host,
        "frames": frames,
        "time": timestamp,
        "data_time": data_time.isoformat(timespec="minutes"),
        "age_minutes": age_minutes,
        "source": source,
        "status": f"{labels[source]} · vor {age_minutes} min",
        "path": path,
        "tile_url": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
    }


def get_radar_metadata(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    base = _base(cfg)
    errors: list[str] = []
    try:
        data = _fetch_json(WEATHER_URL)
        if not isinstance(data, dict):
            raise ValueError("Ungültige RainViewer-Antwort")
        radar = data.get("radar", {})
        past = radar.get("past", []) if isinstance(radar, dict) else []
        nowcast = radar.get("nowcast", []) if isinstance(radar, dict) else []
        frame = _latest(past)
        source = "measurement"
        if frame is None:
            frame = _latest(nowcast)
            source = "nowcast"
        if frame:
            host = str(data.get("host") or DEFAULT_HOST).rstrip("/")
            return _result(base, int(frame.get("time") or 0), str(frame["path"]), host, source, len(past) + len(nowcast))
    except Exception as exc:
        errors.append(_short_error(exc))
        LOGGER.warning("RainViewer-Metadaten fehlgeschlagen: %s", exc)

    try:
        legacy = _fetch_json(LEGACY_URL)
        stamps = sorted(int(item) for item in legacy if str(item).isdigit()) if isinstance(legacy, list) else []
        if stamps:
            timestamp = stamps[-1]
            return _result(base, timestamp, f"/v2/radar/{timestamp}", DEFAULT_HOST, "legacy", len(stamps))
    except Exception as exc:
        errors.append(_short_error(exc))
        LOGGER.warning("RainViewer-Legacy-Fallback fehlgeschlagen: %s", exc)

    return {
        **base,
        "ok": False,
        "offline": True,
        "frames": 0,
        "source": "offline",
        "status": "Radar offline",
        "error": " / ".join(errors) or "RainViewer nicht erreichbar",
    }
