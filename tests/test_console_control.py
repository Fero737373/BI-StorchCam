from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bi_storchcam import console_control


def test_missing_control_is_reported_as_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(console_control, "control_path", lambda: tmp_path / "missing-control")

    result = console_control.run_console_action("status")

    assert result["ok"] is True
    assert result["available"] is False
    assert result["state"] == "unavailable"


def test_status_returns_stopped_without_using_real_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "console-control"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(console_control, "control_path", lambda: script)
    monkeypatch.setattr(console_control.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        console_control,
        "_run",
        lambda _command, **_kwargs: subprocess.CompletedProcess(_command, 0, stdout="stopped\n", stderr=""),
    )

    result = console_control.run_console_action("status")

    assert result == {
        "ok": True,
        "available": True,
        "state": "stopped",
        "message": "stopped",
    }


def test_toggle_failure_is_exposed_as_control_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "console-control"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(console_control, "control_path", lambda: script)
    monkeypatch.setattr(console_control.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        console_control,
        "_run",
        lambda _command, **_kwargs: subprocess.CompletedProcess(_command, 1, stdout="unavailable\n", stderr="Docker fehlt"),
    )
    monkeypatch.setattr(console_control, "_run_as_docker_group", lambda _script, _action: None)

    with pytest.raises(console_control.ConsoleControlError, match="Docker fehlt"):
        console_control.run_console_action("toggle")


def test_bluetooth_success_is_returned_without_docker_group_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "console-control"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(console_control, "control_path", lambda: script)
    monkeypatch.setattr(console_control.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        console_control,
        "_run",
        lambda _command, **_kwargs: subprocess.CompletedProcess(
            _command,
            0,
            stdout="connected\nController verbunden: 8BitDo Pro 2\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        console_control,
        "_run_as_docker_group",
        lambda *_args: pytest.fail("Bluetooth darf nicht über die Docker-Gruppe laufen"),
    )

    result = console_control.run_console_action("bluetooth")

    assert result == {
        "ok": True,
        "available": True,
        "state": "connected",
        "message": "Controller verbunden: 8BitDo Pro 2",
    }
