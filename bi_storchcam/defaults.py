# -*- coding: utf-8 -*-
"""Default-Konfiguration für BI-StorchCam.

Private lokale Daten gehören unter Linux nach ~/.config/BI-StorchCam/config.json
und unter Windows nach %APPDATA%\\BI-StorchCam\\config.json.
"""

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
        "url": "https://www.youtube.com/embed/kgaMXfx0G8U?autoplay=1&mute=1&playsinline=1&controls=0&modestbranding=1&rel=0",
        "muted": True,
        "autoplay": True,
    },
    "ui": {
        "menu_enabled": True,
        "theme": "dark-radar",
        "layout_profile": "auto",
        "clock": {"enabled": True, "position": "top-left", "size": "auto"},
        "weather": {"enabled": True, "mode": "smart_short", "position": "bottom", "size": "auto"},
        "radar": {
            "enabled": True,
            "position": "left",
            "width": 260,
            "height": 190,
            "zoom": 10,
            "opacity": 0.82,
            "refresh_seconds": 300,
        },
        "transit": {"enabled": True, "position": "right", "size": "auto"},
        "system": {"enabled": True, "position": "top-right", "diagnostic_only": False},
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
        "stops": [
            {
                "title": "BEISPIEL",
                "station_name": "Gellershagen Schneiderstraße",
                "station_id": "23005489",
                "line_filter": ["31"],
                "nightbus_only": False,
                "hide_if_empty": False,
                "max_rows": 2,
            }
        ],
    },
}
