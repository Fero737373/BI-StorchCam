# -*- coding: utf-8 -*-
"""Default-Konfiguration für BI-StorchCam."""

DEFAULT_CONFIG = {
    "app": {
        "name": "BI-StorchCam",
        "language": "de",
        "timezone": "Europe/Berlin",
        "cache_dir": "~/.cache/BI-StorchCam",
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "state_refresh_seconds": 2,
    },
    "kiosk": {
        "enabled": True,
        "display": ":0",
        "xauthority": "~/.Xauthority",
        "browser": "auto",
        "profile_dir": "",
        "kill_existing_chromium": True,
        "disable_screensaver": True,
        "use_gpu": True,
        "extra_flags": [],
    },
    "screen": {
        "profile": "auto",
        "width": 1280,
        "height": 720,
        "output": "DSI-2",
        "rotation": "right",
        "touch_matrix": "0 1 0 -1 0 1 0 0 1",
    },
    "location": {
        "label": "Bielefeld",
        "latitude": 52.0302,
        "longitude": 8.5325,
    },
    "stream": {
        "url": "",
        "muted": True,
        "autoplay": True,
    },
    "ui": {
        "menu_enabled": True,
        "theme": "production",
        "layout_profile": "auto",
        "clock": {"enabled": True, "position": "top-left", "size": "large"},
        "weather": {"enabled": True, "mode": "smart_short", "position": "bottom", "size": "large"},
        "radar": {
            "enabled": True,
            "position": "left",
            "width": 420,
            "height": 320,
            "zoom": 12,
            "opacity": 0.92,
            "refresh_seconds": 300,
        },
        "transit": {"enabled": False, "position": "right", "size": "auto"},
        "system": {"enabled": False, "position": "top-right", "diagnostic_only": True},
    },
    "weather": {
        "provider": "openmeteo",
        "refresh_seconds": 300,
        "forecast_hours": 8,
        "rain_mm_threshold": 0.1,
        "rain_probability_threshold": 45,
    },
    "transit": {
        "provider": "vrr",
        "refresh_seconds": 60,
        "default_max_rows": 2,
        "target_len": 16,
        "stops": [],
    },
}
