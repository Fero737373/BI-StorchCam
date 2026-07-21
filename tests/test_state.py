from __future__ import annotations

import time
from pathlib import Path

import pytest

from bi_storchcam.state import StateManager


def test_central_snapshot_and_config_invalidation(monkeypatch: pytest.MonkeyPatch, config: dict, tmp_path: Path) -> None:
    config["app"]["cache_dir"] = str(tmp_path)
    monkeypatch.setattr("bi_storchcam.state.get_weather", lambda _cfg, force=False: {"ok": True, "text": "sonnig"})
    monkeypatch.setattr("bi_storchcam.state.get_radar_metadata", lambda _cfg: {"ok": True})
    monkeypatch.setattr("bi_storchcam.state.get_boards", lambda _cfg, force=False: [])
    manager = StateManager(config)
    manager.refresh_all()
    assert manager.snapshot()["weather"]["text"] == "sonnig"
    assert not (tmp_path / "storch_data.json").exists()
    changed = {**config, "location": {**config["location"], "label": "Herford"}}
    manager.update_config(changed)
    assert manager.snapshot()["config"]["location"]["label"] == "Herford"
    assert manager._last_run == {}


def test_provider_failure_does_not_end_worker(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    def fail(*_args, **_kwargs):
        raise OSError("provider offline")

    monkeypatch.setattr("bi_storchcam.state.get_weather", fail)
    monkeypatch.setattr("bi_storchcam.state.get_radar_metadata", fail)
    monkeypatch.setattr("bi_storchcam.state.get_boards", fail)
    manager = StateManager(config)
    manager.start()
    assert manager.wait_ready(2)
    time.sleep(0.05)
    assert manager._thread is not None and manager._thread.is_alive()
    manager.stop()
