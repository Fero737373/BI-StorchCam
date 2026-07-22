"""Thread-safe background state snapshots; API reads never call external providers."""

from __future__ import annotations

import copy
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import partial
from typing import Any

from .providers.rainviewer import get_radar_metadata
from .providers.transit_vrr_smart import get_boards
from .providers.weather_smart import get_weather
from .system_status import get_system_status

LOGGER = logging.getLogger(__name__)


class StateManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self._lock = threading.RLock()
        self._config = copy.deepcopy(config)
        self._snapshot: dict[str, Any] = self._empty_snapshot(config)
        self._last_run: dict[str, float] = {}
        self._generation = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    @staticmethod
    def _public_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy({
            "ui": config.get("ui", {}),
            "screen": config.get("screen", {}),
            "stream": config.get("stream", {}),
            "location": config.get("location", {}),
            "timezone": config.get("app", {}).get("timezone", "Europe/Berlin"),
            "transit_provider": config.get("transit", {}).get("provider", "vrr"),
        })

    def _empty_snapshot(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "generated_at": None,
            "config": self._public_runtime_config(config),
            "weather": {"ok": False, "text": "Wetter wird geladen"},
            "radar": {"ok": False, "status": "Radar wird geladen", "offline": False},
            "boards": [],
            "system": {"enabled": bool(config.get("ui", {}).get("system", {}).get("enabled", False))},
        }

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="storchcam-state", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def update_config(self, config: dict[str, Any]) -> None:
        with self._lock:
            if config != self._config:
                self._config = copy.deepcopy(config)
                self._snapshot["config"] = self._public_runtime_config(config)
                self._last_run.clear()
                self._generation += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._snapshot)

    def wait_ready(self, timeout: float) -> bool:
        return self._ready.wait(timeout)

    def refresh_all(self) -> None:
        with self._lock:
            config = copy.deepcopy(self._config)
            generation = self._generation
        updates: dict[str, Any] = {}
        tasks: list[tuple[str, Callable[[], Any]]] = [
            ("weather", lambda: get_weather(config, force=True)),
            ("radar", lambda: get_radar_metadata(config)),
            ("boards", lambda: get_boards(config, force=True)),
        ]
        if config.get("ui", {}).get("system", {}).get("enabled", False):
            tasks.append(("system", get_system_status))
        else:
            updates["system"] = {"enabled": False}
        for name, task in tasks:
            try:
                updates[name] = task()
            except Exception as exc:
                LOGGER.exception("State-Provider %s fehlgeschlagen", name)
                updates[name] = {"ok": False, "error": str(exc)[:160]} if name != "boards" else []
        updates["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            if generation == self._generation:
                self._snapshot.update(updates)
                completed = time.monotonic()
                self._last_run.update({name: completed for name, _task in tasks})
        self._ready.set()

    def _due(self, name: str, interval: int, now: float) -> bool:
        with self._lock:
            return now - self._last_run.get(name, 0) >= interval

    def _run(self) -> None:
        self._ready.set()
        self.refresh_all()
        while not self._stop.wait(1):
            with self._lock:
                config = copy.deepcopy(self._config)
                generation = self._generation
            now = time.monotonic()
            tasks: list[tuple[str, int, Callable[[], Any]]] = [
                ("weather", int(config["weather"]["refresh_seconds"]), partial(get_weather, config, force=True)),
                ("radar", int(config["radar"]["refresh_seconds"]), partial(get_radar_metadata, config)),
                ("boards", int(config["transit"]["refresh_seconds"]), partial(get_boards, config, force=True)),
            ]
            if config.get("ui", {}).get("system", {}).get("enabled", False):
                tasks.append(("system", 5, get_system_status))
            for name, interval, task in tasks:
                if not self._due(name, interval, now):
                    continue
                try:
                    value = task()
                except Exception as exc:
                    LOGGER.exception("State-Provider %s fehlgeschlagen", name)
                    value = {"ok": False, "error": str(exc)[:160]} if name != "boards" else []
                with self._lock:
                    if generation == self._generation:
                        self._snapshot[name] = value
                        self._snapshot["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                        self._last_run[name] = time.monotonic()
