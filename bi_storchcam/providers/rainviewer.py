# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import urllib.request
from typing import Any

RAINVIEWER_URL = "https://api.rainviewer.com/public/weather-maps.json"


def get_radar_metadata() -> dict[str, Any]:
    req = urllib.request.Request(RAINVIEWER_URL, headers={"User-Agent": "BI-StorchCam/2.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    frames = []
    radar = data.get("radar", {})
    frames.extend(radar.get("past", []) or [])
    frames.extend(radar.get("nowcast", []) or [])
    return {"ok": bool(frames), "host": data.get("host"), "frames": len(frames)}
