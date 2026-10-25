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

from .providers.transit_vrr_smart import get_boards
from .providers.weather_smart import get_weather
from .system_status import get_system_status

LOGGER = logging.getLogger(__name__)
SYSTEM_REFRESH_SECONDS = 5

ProviderTask = tuple[str, int, Callable[[], Any]]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _system_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("ui", {}).get("system", {}).get("enabled", False))


def _provider_tasks(config: dict[str, Any]) -> list[ProviderTask]:
    tasks: list[ProviderTask] = [
        ("weather", int(config["weather"]["refresh_seconds"]), partial(get_weather, config, force=True)),
        ("boards", int(config["transit"]["refresh_seconds"]), partial(get_boards, config, force=True)),
    ]
    if _system_enabled(config):
        tasks.append(("system", SYSTEM_REFRESH_SECONDS, get_system_status))
    return tasks


def _fetch(name: str, task: Callable[[], Any]) -> Any:
    try:
        return task()
    except Exception as exc:
        LOGGER.exception("State-Provider %s fehlgeschlagen", name)
        return [] if name == "boards" else {"ok": False, "error": str(exc)[:160]}


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
            "transit_stop_count": len(config.get("transit", {}).get("stops", [])),
        })

    def _empty_snapshot(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "generated_at": None,
            "config": self._public_runtime_config(config),
            "weather": {"ok": False, "text": "Wetter wird geladen"},
            "boards": [],
            "system": {"enabled": _system_enabled(config)},
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

    def _config_and_generation(self) -> tuple[dict[str, Any], int]:
        with self._lock:
            return copy.deepcopy(self._config), self._generation

    def refresh_all(self) -> None:
        config, generation = self._config_and_generation()
        tasks = _provider_tasks(config)
        updates: dict[str, Any] = {name: _fetch(name, task) for name, _interval, task in tasks}
        if not _system_enabled(config):
            updates["system"] = {"enabled": False}
        updates["generated_at"] = _utc_timestamp()
        with self._lock:
            if generation == self._generation:
                self._snapshot.update(updates)
                completed = time.monotonic()
                self._last_run.update({name: completed for name, _interval, _task in tasks})
        self._ready.set()

    def _due(self, name: str, interval: int, now: float) -> bool:
        with self._lock:
            return now - self._last_run.get(name, 0) >= interval

    def _refresh_due(self) -> None:
        config, generation = self._config_and_generation()
        now = time.monotonic()
        for name, interval, task in _provider_tasks(config):
            if not self._due(name, interval, now):
                continue
            value = _fetch(name, task)
            with self._lock:
                if generation == self._generation:
                    self._snapshot[name] = value
                    self._snapshot["generated_at"] = _utc_timestamp()
                    self._last_run[name] = time.monotonic()

    def _run(self) -> None:
        self._ready.set()
        self.refresh_all()
        while not self._stop.wait(1):
            self._refresh_due()
