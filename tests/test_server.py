from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bi_storchcam.server import ServerContext, StorchServer, run_server
from bi_storchcam.state import StateManager


@contextmanager
def running_server(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[tuple[str, int]]:
    monkeypatch.setenv("BI_STORCHCAM_CONFIG", str(tmp_path / "config.json"))
    state = StateManager(config)
    state._ready.set()
    server = StorchServer(("127.0.0.1", 0), ServerContext(config, state))
    thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def request(address: tuple[str, int], method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    raw = response.read()
    result = json.loads(raw) if response.getheader("Content-Type", "").startswith("application/json") else raw
    snapshot = (response.status, dict(response.getheaders()), result)
    connection.close()
    return snapshot


def post_json(address: tuple[str, int], path: str, value: dict, token: str = ""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return request(address, "POST", path, json.dumps(value).encode(), headers)


def test_health_state_and_static_security_headers(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with running_server(config, monkeypatch, tmp_path) as address:
        status, _headers, health = request(address, "GET", "/api/health")
        assert status == 200 and health["ok"] and health["state_ready"] and health["version"] == "0.2.0b1"
        status, _headers, state = request(address, "GET", "/api/state")
        assert status == 200 and "config" in state
        status, headers, body = request(address, "GET", "/")
        assert status == 200 and b"BI-StorchCam" in body
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_admin_setup_login_and_config_write(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with running_server(config, monkeypatch, tmp_path) as address:
        status, _headers, setup = post_json(address, "/api/admin/setup", {"pin": "1234"})
        assert status == 200 and setup["token"]
        token = setup["token"]
        status, _headers, payload = request(address, "GET", "/api/config")
        assert status == 401 and payload["ok"] is False
        status, _headers, payload = request(address, "GET", "/api/config", headers={"Authorization": f"Bearer {token}"})
        assert status == 200 and payload["config"]["admin"]["pin_hash"] == ""
        candidate = payload["config"]
        candidate["location"]["label"] = "Herford"
        status, _headers, saved = post_json(address, "/api/config/save", {"config": candidate}, token)
        assert status == 200 and saved["config"]["location"]["label"] == "Herford"
        status, _headers, login = post_json(address, "/api/admin/login", {"pin": "1234"})
        assert status == 200 and login["token"]
        status, _headers, denied = post_json(address, "/api/admin/login", {"pin": "9999"})
        assert status == 401 and denied["error"] == "PIN ist falsch"


def test_bad_json_large_request_and_status_codes(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config["server"]["max_request_bytes"] = 4096
    with running_server(config, monkeypatch, tmp_path) as address:
        status, _headers, body = request(address, "POST", "/api/admin/login", b"{broken", {"Content-Type": "application/json"})
        assert status == 400 and body["error"] == "Ungültiges JSON"
        status, _headers, body = request(address, "POST", "/api/admin/login", b"x" * 5000, {"Content-Type": "application/json"})
        assert status == 413 and body["error"] == "Request ist zu groß"
        status, _headers, body = post_json(address, "/api/config/save", {"config": config})
        assert status == 401
        status, _headers, body = post_json(address, "/api/does-not-exist", {})
        assert status == 404


def test_state_endpoint_does_not_call_provider(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Provider darf nicht durch API aufgerufen werden")

    monkeypatch.setattr("bi_storchcam.providers.weather_smart.get_weather", forbidden)
    with running_server(config, monkeypatch, tmp_path) as address:
        assert request(address, "GET", "/api/state")[0] == 200


def test_local_console_and_bluetooth_endpoints(config: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    actions: list[str] = []

    def fake_console_action(action: str) -> dict[str, object]:
        actions.append(action)
        state = "connected" if action == "bluetooth" else "stopped"
        return {"ok": True, "available": True, "state": state, "message": state}

    monkeypatch.setattr("bi_storchcam.server.run_console_action", fake_console_action)
    with running_server(config, monkeypatch, tmp_path) as address:
        assert request(address, "GET", "/api/console/status")[0] == 200
        assert post_json(address, "/api/console/toggle", {})[0] == 200
        status, _headers, payload = post_json(address, "/api/console/bluetooth", {})
        assert status == 200 and payload["state"] == "connected"

    assert actions == ["status", "toggle", "bluetooth"]
