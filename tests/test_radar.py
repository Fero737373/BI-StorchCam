from __future__ import annotations

import pytest

from bi_storchcam.providers import rainviewer


def test_measurement_and_nowcast(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    monkeypatch.setattr(rainviewer, "_fetch_json", lambda _url: {"host": "https://tilecache.rainviewer.com", "radar": {"past": [{"time": 1_700_000_000, "path": "/past"}], "nowcast": []}})
    result = rainviewer.get_radar_metadata(config)
    assert result["ok"] and result["source"] == "measurement" and result["data_time"]

    monkeypatch.setattr(rainviewer, "_fetch_json", lambda _url: {"radar": {"past": [], "nowcast": [{"time": 1_700_000_100, "path": "/future"}]}})
    assert rainviewer.get_radar_metadata(config)["source"] == "nowcast"


def test_legacy_and_offline(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    def legacy(url: str):
        if url == rainviewer.WEATHER_URL:
            raise OSError("primary down")
        return [1_700_000_000]

    monkeypatch.setattr(rainviewer, "_fetch_json", legacy)
    assert rainviewer.get_radar_metadata(config)["source"] == "legacy"
    monkeypatch.setattr(rainviewer, "_fetch_json", lambda _url: (_ for _ in ()).throw(OSError("offline")))
    result = rainviewer.get_radar_metadata(config)
    assert result["offline"] and result["status"] == "Radar offline" and "attribution" in result
