# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config_store import cache_dir
from .providers.transit_vrr_smart import get_boards
from .providers.weather_smart import get_weather
from .system_status import get_system_status


def build_state(config: dict[str, Any]) -> dict[str, Any]:
    state = {
        "ts": datetime.now().strftime("%H:%M:%S"),
        "config": {
            "ui": config.get("ui", {}),
            "screen": config.get("screen", {}),
            "stream": config.get("stream", {}),
            "location": config.get("location", {}),
        },
        "system": get_system_status(),
        "weather": get_weather(config),
        "boards": get_boards(config),
    }
    try:
        out = cache_dir(config) / "storch_data.json"
        out.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return state
