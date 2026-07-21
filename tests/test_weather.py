from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bi_storchcam.providers import weather_smart


def hourly_data() -> dict:
    return {
        "time": ["2026-07-21T08:00", "2026-07-21T09:00", "2026-07-21T10:00", "2026-07-21T11:00"],
        "precipitation": [9, 8, 0, 1.2],
        "precipitation_probability": [99, 99, 5, 70],
        "weather_code": [63, 63, 1, 61],
    }


def test_forecast_starts_at_current_or_future_hour() -> None:
    now = datetime(2026, 7, 21, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    selected = weather_smart.future_forecast(hourly_data(), "Europe/Berlin", 2, now)
    assert [item["time"].hour for item in selected] == [10, 11]


def test_dst_timezone_is_respected() -> None:
    hourly = {"time": ["2026-10-25T01:00", "2026-10-25T03:00"], "precipitation": [0, 1], "precipitation_probability": [0, 80], "weather_code": [1, 61]}
    now = datetime(2026, 10, 25, 2, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    selected = weather_smart.future_forecast(hourly, "Europe/Berlin", 8, now)
    assert [item["time"].hour for item in selected] == [3]


def test_weather_cache_key_changes_with_location(config: dict) -> None:
    before = weather_smart.cache_key(config)
    config["location"]["latitude"] = 52.1
    assert weather_smart.cache_key(config) != before


def test_weather_offline_uses_last_valid_snapshot(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    weather_smart.clear_cache()
    response = {
        "current": {"temperature_2m": 20, "apparent_temperature": 19, "relative_humidity_2m": 50, "precipitation": 0, "weather_code": 1, "wind_speed_10m": 10},
        "hourly": hourly_data(),
    }
    monkeypatch.setattr(weather_smart, "_fetch_json", lambda _url: response)
    now = datetime(2026, 7, 21, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    assert weather_smart.get_weather(config, force=True, now=now)["ok"]
    monkeypatch.setattr(weather_smart, "_fetch_json", lambda _url: (_ for _ in ()).throw(OSError("offline")))
    fallback = weather_smart.get_weather(config, force=True, now=now)
    assert fallback["ok"] and fallback["stale"] and fallback["error"] == "offline"
