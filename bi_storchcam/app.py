from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .browser import launch_stream
from .config import config_exists, load_config
from .overlay import OverlayApp
from .setup_wizard import run_setup


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="BI-StorchCam")
    parser.add_argument("--setup", action="store_true", help="Setup öffnen und Konfiguration speichern")
    parser.add_argument("--no-browser", action="store_true", help="Nur Overlay starten, keinen Browser öffnen")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.setup or not config_exists():
        config = run_setup(load_config())
    else:
        config = load_config()

    if not args.no_browser:
        video = config.get("video", {})
        url = video.get("url") or "https://www.youtube.com/watch?v=mRECZ-PJ2So"
        fullscreen = bool(video.get("fullscreen", True))
        launch_stream(url, fullscreen=fullscreen)
        time.sleep(4)

    overlay = OverlayApp(config)
    overlay.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
