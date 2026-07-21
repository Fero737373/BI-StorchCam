from __future__ import annotations

import pytest

from bi_storchcam.providers import transit_vrr_smart as transit


def stop(station_id: str = "23000001") -> dict:
    return {
        "title": "Jahnplatz",
        "station_name": "Bielefeld Jahnplatz",
        "station_id": station_id,
        "line_filter": ["31", "N"],
        "nightbus_only": False,
        "hide_if_empty": False,
        "max_rows": 3,
    }


def departures() -> dict:
    return {
        "departureData": [
            {"lineNumber": "31", "direction": "Bielefeld, Schildesche", "countdown": 2},
            {"lineNumber": "4", "direction": "Universität", "countdown": 3},
            {"lineNumber": "N2", "direction": "Babenhausen", "countdown": 5},
        ]
    }


def test_cache_key_includes_complete_stop_configuration(config: dict) -> None:
    config["transit"]["stops"] = [stop()]
    before = transit.cache_key(config)
    config["transit"]["stops"][0]["station_id"] = "other"
    assert transit.cache_key(config) != before


def test_line_and_nightbus_filters(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    transit.clear_cache()
    config["transit"]["stops"] = [stop()]
    monkeypatch.setattr(transit, "_fetch_json", lambda _url, _data=None, timeout=12: departures())
    board = transit.get_boards(config, force=True)[0]
    assert [row["line"] for row in board["rows"]] == ["31", "N2"]
    config["transit"]["stops"][0]["nightbus_only"] = True
    board = transit.get_boards(config, force=True)[0]
    assert [row["line"] for row in board["rows"]] == ["N2"]


def test_multiple_stops_and_error_do_not_mutate_config(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    transit.clear_cache()
    config["transit"]["stops"] = [stop("one"), {**stop("two"), "title": "Zwei"}]
    calls = 0

    def fake(_url: str, data=None, timeout=12):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("VRR offline")
        return departures()

    monkeypatch.setattr(transit, "_fetch_json", fake)
    boards = transit.get_boards(config, force=True)
    assert len(boards) == 2 and boards[1]["ok"] is False
    assert "last_error" not in config["transit"]["stops"][1]
