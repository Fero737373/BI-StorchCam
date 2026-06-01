from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class Weather:
    condition: str
    temperature: int
    feels_like: int
    wind_kmh: int
    humidity: int
    rain_mm: float


WEATHER_CODES = {
    0: "Klar",
    1: "Meist klar",
    2: "Teils bewölkt",
    3: "Bewölkt",
    45: "Nebel",
    48: "Reifnebel",
    51: "Leichter Niesel",
    53: "Niesel",
    55: "Starker Niesel",
    61: "Leichter Regen",
    63: "Regen",
    65: "Starker Regen",
    71: "Leichter Schnee",
    73: "Schnee",
    75: "Starker Schnee",
    80: "Schauer",
    81: "Schauer",
    82: "Starke Schauer",
    95: "Gewitter",
}


def _fetch_json(url: str) -> object:
    headers = {
        "User-Agent": "BI-StorchCam/0.1",
        "Accept": "application/json,text/plain,*/*",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def get_weather(latitude: float, longitude: float) -> Weather:
    params = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "Europe/Berlin",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    data = _fetch_json(url)
    current = data.get("current", {}) if isinstance(data, dict) else {}

    return Weather(
        condition=WEATHER_CODES.get(current.get("weather_code"), "Aktuell"),
        temperature=round(float(current.get("temperature_2m", 0))),
        feels_like=round(float(current.get("apparent_temperature", 0))),
        wind_kmh=round(float(current.get("wind_speed_10m", 0))),
        humidity=round(float(current.get("relative_humidity_2m", 0))),
        rain_mm=float(current.get("precipitation", 0)),
    )


def format_weather(label: str, weather: Weather) -> str:
    short_label = label.split(",")[0].strip() or "Bielefeld"
    return (
        f"{short_label} | {weather.condition} | {weather.temperature} °C | "
        f"gefühlt {weather.feels_like} °C | Wind {weather.wind_kmh} km/h | "
        f"Feuchte {weather.humidity}% | Regen {weather.rain_mm:.1f} mm"
    )
