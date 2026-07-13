# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from typing import Any

from .config_store import CONFIG_PATH, config_path, load_config, save_config
from .kiosk import browser_is_running, start_browser, stop_browser
from .providers.rainviewer import get_radar_metadata
from .providers.transit_vrr_smart import get_boards, search_station
from .providers.weather_smart import get_weather
from .server import run_server
from .state import build_state


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _positive_float(value: Any, fallback: float, minimum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(minimum, parsed)


def setup_interactive() -> None:
    cfg = load_config()
    print("BI-StorchCam Setup")
    print("Enter = aktuellen Wert behalten")

    loc = cfg.setdefault("location", {})
    label = input(f"Standort Label [{loc.get('label', 'Bielefeld')}]: ").strip()
    if label:
        loc["label"] = label

    stream = cfg.setdefault("stream", {})
    url = input(f"Stream/YouTube Embed URL [{stream.get('url', '')}]: ").strip()
    if url:
        stream["url"] = url

    print("\nHaltestellen stellst du später bequem im Touch-Menü ein.")
    save_config(cfg)
    print(f"Gespeichert: {CONFIG_PATH}")


def start_local_server(cfg: dict[str, Any]) -> tuple[str, threading.Thread]:
    host = str(cfg.get("server", {}).get("host", "127.0.0.1"))
    port = int(cfg.get("server", {}).get("port", 8000))
    thread = threading.Thread(target=run_server, args=(host, port), daemon=True)
    thread.start()
    url = f"http://{host}:{port}/"
    return url, thread


def _restart_settings(cfg: dict[str, Any]) -> tuple[float, float, float]:
    kiosk = cfg.get("kiosk", {})
    initial = _positive_float(kiosk.get("browser_restart_seconds"), 3.0, 2.0)
    maximum = _positive_float(kiosk.get("browser_restart_max_seconds"), 60.0, initial)
    stable = _positive_float(kiosk.get("browser_stable_seconds"), 30.0, 10.0)
    return initial, maximum, stable


def main() -> None:
    parser = argparse.ArgumentParser(description="BI-StorchCam Kiosk")
    parser.add_argument("--setup", action="store_true", help="Text-Setup ausführen")
    parser.add_argument("--kiosk", action="store_true", help="Server + Chromium-Kiosk starten")
    parser.add_argument("--no-browser", action="store_true", help="Nur lokalen Server starten")
    parser.add_argument("--test-config", action="store_true", help="Config laden und anzeigen")
    parser.add_argument("--test-weather", action="store_true", help="Open-Meteo testen")
    parser.add_argument("--test-transit", action="store_true", help="VRR-Abfahrten testen")
    parser.add_argument("--test-radar", action="store_true", help="RainViewer testen")
    parser.add_argument("--station-search", default="", help="VRR-Haltestelle suchen")
    args = parser.parse_args()

    cfg_path = config_path()
    cfg = load_config(cfg_path)

    if args.setup:
        setup_interactive()
        return
    if args.test_config:
        _print_json({"path": str(cfg_path), "config": cfg})
        return
    if args.test_weather:
        _print_json(get_weather(cfg))
        return
    if args.station_search:
        _print_json(search_station(args.station_search))
        return
    if args.test_transit:
        _print_json(get_boards(cfg))
        return
    if args.test_radar:
        _print_json(get_radar_metadata())
        return

    url, _thread = start_local_server(cfg)
    print(f"BI-StorchCam Server läuft: {url}")
    print(f"Lokale Config: {cfg_path}")

    browser_process: subprocess.Popen[Any] | None = None
    browser_started_at: float | None = None
    next_browser_start = 0.0
    restart_delay, restart_max, stable_seconds = _restart_settings(cfg)

    if not args.no_browser and cfg.get("kiosk", {}).get("enabled", True):
        browser_process = start_browser(cfg, url)
        if browser_process is not None:
            browser_started_at = time.monotonic()

    try:
        while True:
            loop_started = time.monotonic()
            current_cfg = load_config(cfg_path)

            try:
                build_state(current_cfg)
            except Exception as exc:
                print(f"WARNUNG: State-Aktualisierung fehlgeschlagen: {exc}")

            browser_enabled = not args.no_browser and current_cfg.get("kiosk", {}).get("enabled", True)
            if not browser_enabled:
                if browser_is_running(browser_process):
                    print("Kiosk-Browser wurde per Konfiguration deaktiviert.")
                    stop_browser(browser_process)
                browser_process = None
                browser_started_at = None
            else:
                now = time.monotonic()
                current_initial, current_max, current_stable = _restart_settings(current_cfg)
                restart_max = current_max
                stable_seconds = current_stable

                if browser_is_running(browser_process):
                    if browser_started_at is not None and now - browser_started_at >= stable_seconds:
                        restart_delay = current_initial
                else:
                    if browser_process is not None:
                        exit_code = browser_process.poll()
                        lifetime = now - browser_started_at if browser_started_at is not None else 0.0
                        print(f"WARNUNG: Chromium wurde beendet (Code {exit_code}, Laufzeit {lifetime:.1f}s).")
                        if lifetime < stable_seconds:
                            restart_delay = min(max(restart_delay * 2, current_initial), restart_max)
                        else:
                            restart_delay = current_initial
                        next_browser_start = max(next_browser_start, now + restart_delay)
                        browser_process = None
                        browser_started_at = None

                    if browser_process is None and now >= next_browser_start:
                        print(f"Starte Chromium-Watchdog neu (Wartezeit {restart_delay:.0f}s bei erneutem Fehler).")
                        browser_process = start_browser(current_cfg, url)
                        if browser_process is not None:
                            browser_started_at = time.monotonic()
                        else:
                            next_browser_start = now + restart_delay
                            restart_delay = min(max(restart_delay * 2, current_initial), restart_max)

            refresh_seconds = _positive_float(
                current_cfg.get("server", {}).get("state_refresh_seconds"),
                2.0,
                1.0,
            )
            elapsed = time.monotonic() - loop_started
            time.sleep(max(0.2, refresh_seconds - elapsed))
    except KeyboardInterrupt:
        print("Beendet.")
    finally:
        stop_browser(browser_process)
