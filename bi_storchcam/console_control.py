"""Local, narrowly scoped bridge to the Pegasus container controller."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

ConsoleState = Literal["running", "stopped", "unavailable"]
VALID_STATES: set[str] = {"running", "stopped", "unavailable"}


@dataclass(frozen=True)
class ConsoleStatus:
    state: ConsoleState
    message: str = ""

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "ok": self.state != "unavailable",
            "available": self.state != "unavailable",
            "state": self.state,
            "message": self.message,
        }


class ConsoleController:
    """Run only the fixed KonsolenDocker control script, never a shell command."""

    def __init__(self, executable: str | Path | None = None) -> None:
        configured = executable or os.environ.get("STORCHCAM_CONSOLE_CONTROL")
        self.executable = (
            Path(configured).expanduser()
            if configured
            else Path.home() / "KonsolenDocker" / "bin" / "console-control"
        )

    def status(self) -> ConsoleStatus:
        return self._run("status", timeout=5)

    def toggle(self) -> ConsoleStatus:
        return self._run("toggle", timeout=45)

    def _run(self, action: Literal["status", "toggle"], *, timeout: int) -> ConsoleStatus:
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            return ConsoleStatus(
                "unavailable",
                f"Konsolensteuerung fehlt oder ist nicht ausführbar: {self.executable}",
            )

        try:
            result = subprocess.run(
                [str(self.executable), action],
                cwd=self.executable.parent.parent,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return ConsoleStatus("unavailable", f"Konsolensteuerung fehlgeschlagen: {exc}")

        stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        parsed = next((line for line in reversed(stdout_lines) if line in VALID_STATES), None)
        details = self._details(result.stderr, stdout_lines)

        if result.returncode != 0:
            return ConsoleStatus("unavailable", details or f"Konsolensteuerung endete mit Code {result.returncode}.")
        if parsed not in VALID_STATES:
            return ConsoleStatus("unavailable", details or "Ungültige Antwort der Konsolensteuerung.")
        return ConsoleStatus(cast(ConsoleState, parsed), details)

    @staticmethod
    def _details(stderr: str, stdout_lines: list[str]) -> str:
        lines = [
            line.strip()
            for line in stderr.splitlines()
            if line.strip() and line.strip() not in VALID_STATES
        ]
        lines.extend(line for line in stdout_lines if line not in VALID_STATES)
        return " · ".join(lines)[:500]
