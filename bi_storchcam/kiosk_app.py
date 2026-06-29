# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any

from .config_store import CONFIG_PATH, config_path, load_config, save_config
from .kiosk import start_browser
from .providers.rainviewer import get_radar_metadata
from .providers.transit_vrr_smart import get_boards, search_station
from .providers.weather_smart import get_weather
from .server import run_server
from .state import build_state


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


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

    if not args.no_browser:
        start_browser(cfg, url)

    try:
        while True:
            build_state(load_config(cfg_path))
            time.sleep(int(cfg.get("server", {}).get("state_refresh_seconds", 2)))
    except KeyboardInterrupt:
        print("Beendet.")
