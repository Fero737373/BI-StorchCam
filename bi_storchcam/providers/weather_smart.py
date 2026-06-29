# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

CODES = {
    0: "klar", 1: "meist klar", 2: "teils bewölkt", 3: "bewölkt",
    45: "Nebel", 48: "Reifnebel",
    51: "leichter Niesel", 53: "Niesel", 55: "starker Niesel",
    61: "leichter Regen", 63: "Regen", 65: "starker Regen",
    71: "leichter Schnee", 73: "Schnee", 75: "starker Schnee",
    80: "Schauer", 81: "Schauer", 82: "starke Schauer", 95: "Gewitter",
}

_cache: dict[str, Any] = {"ts": 0.0, "data": {"ok": False, "text": "Wetter offline"}}


def _fetch_json(url: str, timeout: int = 12) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "BI-StorchCam/2.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _hour_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%H:%M")
    except Exception:
        return value[-5:] if len(value) >= 5 else value


def _smart_text(label: str, current: dict[str, Any], hourly: dict[str, Any], cfg: dict[str, Any]) -> str:
    temp = round(float(current.get("temperature_2m", 0)))
    code = int(current.get("weather_code", 0) or 0)
    condition = CODES.get(code, "aktuell")

    hours = int(cfg.get("forecast_hours", 8))
    rain_limit = float(cfg.get("rain_mm_threshold", 0.1))
    prob_limit = int(cfg.get("rain_probability_threshold", 45))

    times = hourly.get("time", [])[:hours]
    rain = hourly.get("precipitation", [])[:hours]
    probs = hourly.get("precipitation_probability", [])[:hours]

    hint = ""
    for i, amount in enumerate(rain):
        try:
            if float(amount) > rain_limit:
                hint = f"Regen ab {_hour_label(times[i])}"
                break
        except Exception:
            pass

    if not hint:
        for i, prob in enumerate(probs):
            try:
                if int(prob) >= prob_limit:
                    hint = f"Regen möglich ab {_hour_label(times[i])}"
                    break
            except Exception:
                pass

    if not hint:
        end = _hour_label(times[-1]) if times else "später"
        hint = f"trocken bis {end}"

    return f"{label} | {temp}°C | {condition} | {hint}"


def get_weather(config: dict[str, Any]) -> dict[str, Any]:
    weather_cfg = config.get("weather", {})
    refresh = int(weather_cfg.get("refresh_seconds", 300))
    now = time.time()
    if now - float(_cache.get("ts", 0)) < refresh:
        return dict(_cache["data"])

    loc = config.get("location", {})
    lat = loc.get("latitude", 52.0302)
    lon = loc.get("longitude", 8.5325)
    label = loc.get("label", "Bielefeld")

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "hourly": "precipitation,precipitation_probability,weather_code",
        "forecast_days": 1,
        "timezone": config.get("app", {}).get("timezone", "Europe/Berlin"),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    try:
        data = _fetch_json(url)
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        result = {
            "ok": True,
            "label": label,
            "text": _smart_text(label, current, hourly, weather_cfg),
            "condition": CODES.get(int(current.get("weather_code", 0) or 0), "aktuell"),
            "temp": round(float(current.get("temperature_2m", 0))),
            "feels": round(float(current.get("apparent_temperature", 0))),
            "wind": round(float(current.get("wind_speed_10m", 0))),
            "hum": round(float(current.get("relative_humidity_2m", 0))),
            "rain": round(float(current.get("precipitation", 0)), 1),
        }
    except Exception as exc:
        result = {"ok": False, "label": label, "text": f"{label} | Wetter offline", "error": str(exc)}

    _cache["ts"] = now
    _cache["data"] = result
    return dict(result)
