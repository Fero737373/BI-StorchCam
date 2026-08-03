"""Safe local bridge from BI-StorchCam to KonsolenDocker."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Final

DEFAULT_CONTROL: Final = Path("/home/fero/KonsolenDocker/bin/console-control")
VALID_ACTIONS: Final = frozenset({"status", "start", "stop", "toggle", "bluetooth"})
VALID_STATES: Final = frozenset({"running", "stopped", "connected", "unavailable"})


class ConsoleControlError(RuntimeError):
    """Raised when KonsolenDocker cannot be controlled safely."""


def control_path() -> Path:
    override = os.environ.get("BI_STORCHCAM_CONSOLE_CONTROL", "").strip()
    return Path(override).expanduser() if override else DEFAULT_CONTROL


def _run(command: list[str], *, timeout: int = 45) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ConsoleControlError(f"KonsolenDocker reagiert nicht innerhalb von {timeout} Sekunden") from exc
    except OSError as exc:
        raise ConsoleControlError(f"KonsolenDocker konnte nicht ausgeführt werden: {exc}") from exc


def _state(output: str) -> str:
    for line in reversed(output.splitlines()):
        candidate = line.strip().lower()
        if candidate in VALID_STATES:
            return candidate
    return "unavailable"


def _detail(result: subprocess.CompletedProcess[str]) -> str:
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    return lines[-1] if lines else "Keine Rückmeldung von KonsolenDocker"


def _run_as_docker_group(script: Path, action: str) -> subprocess.CompletedProcess[str] | None:
    sg = shutil.which("sg")
    if os.name != "posix" or not sg:
        return None
    fixed_command = f"{shlex.quote(str(script))} {shlex.quote(action)}"
    return _run([sg, "docker", "-c", fixed_command])


def _unavailable(action: str, message: str) -> dict[str, object]:
    if action != "status":
        raise ConsoleControlError(message)
    return {
        "ok": True,
        "available": False,
        "state": "unavailable",
        "message": message,
    }


def run_console_action(action: str) -> dict[str, object]:
    if action not in VALID_ACTIONS:
        raise ValueError(f"Ungültige Konsolen-Aktion: {action}")

    script = control_path()
    if not script.is_file():
        return _unavailable(action, f"KonsolenDocker fehlt unter {script}")
    if not os.access(script, os.X_OK):
        return _unavailable(action, f"KonsolenDocker-Steuerung ist nicht ausführbar: {script}")

    result = _run([str(script), action], timeout=65 if action == "bluetooth" else 45)
    state = _state(result.stdout)

    # Ein bereits laufender systemd-User-Manager kann noch die alte Gruppenliste
    # besitzen. Der feste sg-Aufruf nutzt die aktuelle docker-Gruppenzuordnung,
    # ohne Benutzereingaben in einen Shell-Befehl zu übernehmen.
    if action != "bluetooth" and (result.returncode != 0 or state == "unavailable"):
        grouped = _run_as_docker_group(script, action)
        if grouped is not None:
            result = grouped
            state = _state(result.stdout)

    success_states = {"connected"} if action == "bluetooth" else {"running", "stopped"}
    available = result.returncode == 0 and state in success_states
    payload: dict[str, object] = {
        "ok": available,
        "available": available,
        "state": state if available else "unavailable",
        "message": _detail(result),
    }

    if action != "status" and not available:
        raise ConsoleControlError(str(payload["message"]))
    return payload
