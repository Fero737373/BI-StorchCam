"""Container entry point: prepares the config and starts server plus kiosk browser."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from bi_storchcam.admin import hash_pin
from bi_storchcam.config_store import ConfigError, config_path, load_config, save_config
from bi_storchcam.kiosk_app import main

DISPLAY_WAIT_SECONDS = 300


def _enabled(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def wait_for_display() -> bool:
    """Wartet, bis die Wayland-Sitzung des Hosts (Autologin) ihren Socket angelegt hat."""
    socket = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")) / os.environ.get("WAYLAND_DISPLAY", "wayland-0")
    deadline = time.monotonic() + DISPLAY_WAIT_SECONDS
    announced = False
    while not socket.exists():
        if time.monotonic() >= deadline:
            print(f"WARNUNG: {socket} fehlt nach {DISPLAY_WAIT_SECONDS}s; starte ohne Kiosk-Browser", file=sys.stderr)
            return False
        if not announced:
            print(f"Warte auf Display-Socket {socket} …", file=sys.stderr)
            announced = True
        time.sleep(2)
    return True


def prepare_config() -> int | None:
    path = config_path()
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    # Im Container ist das Menü standardmäßig ohne PIN offen; der Port ist nur auf dem Pi selbst erreichbar.
    config["admin"]["require_pin"] = _enabled("BI_STORCHCAM_REQUIRE_PIN", "0")
    pin = os.environ.get("BI_STORCHCAM_ADMIN_PIN", "").strip()
    if config["admin"]["require_pin"] and not config["admin"]["pin_hash"]:
        if not pin:
            print(
                "FEHLER: Keine Admin-PIN eingerichtet. Entweder BI_STORCHCAM_ADMIN_PIN setzen oder einmalig\n"
                "  docker compose run --rm bi-storchcam --setup\n"
                "ausführen.",
                file=sys.stderr,
            )
            return 2
        try:
            config["admin"]["pin_hash"] = hash_pin(pin)
        except ValueError as exc:
            print(f"FEHLER: BI_STORCHCAM_ADMIN_PIN: {exc}", file=sys.stderr)
            return 2

    stream_url = os.environ.get("BI_STORCHCAM_STREAM_URL", "").strip()
    if stream_url:
        config["stream"]["url"] = stream_url

    # Im Container muss der Server auf allen Interfaces lauschen, damit der Port nach außen erreichbar ist.
    config["server"]["host"] = "0.0.0.0"
    config["server"]["port"] = 8000
    config["kiosk"]["enabled"] = _enabled("BI_STORCHCAM_KIOSK", "1") and wait_for_display()
    try:
        save_config(config, path)
    except ConfigError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2
    return None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        failure = prepare_config()
        if failure is not None:
            raise SystemExit(failure)
    raise SystemExit(main(args))
