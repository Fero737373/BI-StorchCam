from __future__ import annotations

import os
from pathlib import Path

from bi_storchcam.console_control import ConsoleController


def make_controller(tmp_path: Path, body: str) -> ConsoleController:
    executable = tmp_path / "console-control"
    executable.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    executable.chmod(0o755)
    return ConsoleController(executable)


def test_missing_controller_is_unavailable(tmp_path: Path) -> None:
    result = ConsoleController(tmp_path / "missing").status()
    assert result.state == "unavailable"
    assert result.as_dict()["available"] is False


def test_status_parses_controller_state(tmp_path: Path) -> None:
    result = make_controller(tmp_path, 'printf "stopped\\n"').status()
    assert result.state == "stopped"
    assert result.as_dict()["available"] is True


def test_toggle_uses_argument_list_without_shell(tmp_path: Path) -> None:
    marker = tmp_path / "action"
    controller = make_controller(
        tmp_path,
        f'printf "%s" "$1" >"{marker}"\nprintf "running\\n"',
    )
    result = controller.toggle()
    assert result.state == "running"
    assert marker.read_text(encoding="utf-8") == "toggle"
    assert os.access(controller.executable, os.X_OK)
