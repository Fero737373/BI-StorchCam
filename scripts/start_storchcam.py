"""Start BI-StorchCam after local config and kiosk-session cleanup."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


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

    server = raw.get("server")
    changed = isinstance(server, dict) and server.pop("state_refresh_seconds", None) is not None
    if not changed:
        return

    migration_backup = path.with_suffix(path.suffix + ".pre-console-migration.bak")
    if not migration_backup.exists():
        shutil.copy2(path, migration_backup)
    _write_atomic(path, raw)


def _reset_default_browser_profile(config_path: Path) -> None:
    """Discard stale restored tabs from the dedicated temporary kiosk profile."""
    raw = _read_config(config_path) or {}
    kiosk = raw.get("kiosk")
    configured_profile = ""
    if isinstance(kiosk, dict):
        configured_profile = str(kiosk.get("profile_dir", "")).strip()

    # A custom profile can contain user data and is never deleted automatically.
    if configured_profile:
        return

    profile = Path("/tmp/bi-storchcam-browser-profile")
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)


def main() -> int:
    config = _config_path()
    _migrate_file(config)
    _migrate_file(config.with_suffix(config.suffix + ".bak"))
    _reset_default_browser_profile(config)

    from bi_storchcam.kiosk_app import main as application_main

    return application_main()


if __name__ == "__main__":
    raise SystemExit(main())
