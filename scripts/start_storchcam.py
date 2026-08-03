"""Start BI-StorchCam after local config and kiosk-session cleanup."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

BROWSER_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")


def _config_path() -> Path:
    override = os.environ.get("BI_STORCHCAM_CONFIG")
    if override:
        return Path(os.path.expanduser(override))
    return Path.home() / ".config" / "BI-StorchCam" / "config.json"


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _migrate_file(path: Path) -> None:
    raw = _read_config(path)
    if raw is None:
        return

    changed = False
    server = raw.get("server")
    if isinstance(server, dict) and server.pop("state_refresh_seconds", None) is not None:
        changed = True

    kiosk = raw.setdefault("kiosk", {})
    if isinstance(kiosk, dict):
        # Auf dem Pi wird ausschließlich das frische, temporäre Kioskprofil
        # verwendet. Ein altes Profil darf keine API-/JSON-Seite restaurieren.
        if str(kiosk.get("profile_dir", "")).strip():
            kiosk["profile_dir"] = ""
            changed = True
        for obsolete in ("url", "start_url", "startup_url"):
            if kiosk.pop(obsolete, None) is not None:
                changed = True

    if not changed:
        return

    migration_backup = path.with_suffix(path.suffix + ".pre-kiosk-cleanup.bak")
    if not migration_backup.exists():
        shutil.copy2(path, migration_backup)
    _write_atomic(path, raw)


def _stop_existing_browsers() -> None:
    """Stop stale kiosk/default-browser windows before starting the Cam."""
    if os.name == "nt" or shutil.which("pkill") is None:
        return
    for name in BROWSER_NAMES:
        subprocess.run(
            ["pkill", "-TERM", "-x", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    time.sleep(1.5)
    for name in BROWSER_NAMES:
        subprocess.run(
            ["pkill", "-KILL", "-x", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _reset_browser_state() -> None:
    """Delete all known tab/session state used by the Raspberry Pi kiosk."""
    shutil.rmtree(Path("/tmp/bi-storchcam-browser-profile"), ignore_errors=True)

    chromium_default = Path.home() / ".config" / "chromium" / "Default"
    shutil.rmtree(chromium_default / "Sessions", ignore_errors=True)
    for name in ("Current Session", "Current Tabs", "Last Session", "Last Tabs"):
        try:
            (chromium_default / name).unlink(missing_ok=True)
        except OSError:
            pass

    chromium_root = chromium_default.parent
    for name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
        try:
            (chromium_root / name).unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    config = _config_path()
    _migrate_file(config)
    _migrate_file(config.with_suffix(config.suffix + ".bak"))
    _stop_existing_browsers()
    _reset_browser_state()

    from bi_storchcam.kiosk_app import main as application_main

    return application_main()


if __name__ == "__main__":
    raise SystemExit(main())
