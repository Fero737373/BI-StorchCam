from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

BIELEFELD_CENTER_LAT = 52.0302
BIELEFELD_CENTER_LON = 8.5325


@dataclass
class GeoResult:
    label: str
    latitude: float
    longitude: float


def _fetch_json(url: str) -> object:
    headers = {
        "User-Agent": "BI-StorchCam/0.1 (Open-Source Bielefeld Info Screen)",
        "Accept": "application/json,text/plain,*/*",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def geocode_bielefeld(query: str) -> GeoResult:
    clean = (query or "").strip()
    if not clean:
        clean = "Bielefeld"

    if "bielefeld" not in clean.lower():
        clean = f"{clean}, Bielefeld, Deutschland"

    params = {
        "format": "json",
        "limit": "1",
        "addressdetails": "1",
        "countrycodes": "de",
        "bounded": "1",
        # Bielefeld roughly: left, top, right, bottom
        "viewbox": "8.38,52.13,8.73,51.88",
        "q": clean,
    }
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)

    try:
        data = _fetch_json(url)
        if isinstance(data, list) and data:
            item = data[0]
            label = item.get("display_name", "Bielefeld")
            return GeoResult(
                label=str(label).split(", Deutschland")[0],
                latitude=float(item.get("lat")),
                longitude=float(item.get("lon")),
            )
    except Exception:
        pass

    return GeoResult("Bielefeld", BIELEFELD_CENTER_LAT, BIELEFELD_CENTER_LON)
