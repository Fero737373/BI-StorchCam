from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List, Optional

SEARCH_BASE = "https://haltestellenmonitor.vrr.de/backend/api/stations/search?query="
TABLE_URL = "https://haltestellenmonitor.vrr.de/backend/api/stations/table"


@dataclass
class Station:
    station_id: str
    name: str


@dataclass
class Departure:
    line: str
    destination: str
    minutes: str


def _fetch_json(url: str, data: Optional[dict] = None) -> object:
    headers = {
        "User-Agent": "BI-StorchCam/0.1",
        "Accept": "application/json,text/plain,*/*",
    }

    if data is None:
        req = urllib.request.Request(url, headers=headers)
    else:
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _collect_station_items(obj: object) -> list[dict]:
    items: list[dict] = []

    if isinstance(obj, dict):
        if "data" in obj and "value" in obj:
            items.append(obj)
        for value in obj.values():
            items.extend(_collect_station_items(value))
    elif isinstance(obj, list):
        for entry in obj:
            items.extend(_collect_station_items(entry))

    return items


def _query_variants(query: str) -> list[str]:
    clean = (query or "").strip()
    variants = []

    def add(value: str) -> None:
        value = value.strip()
        if value and value not in variants:
            variants.append(value)

    add(clean)
    if clean and "bielefeld" not in clean.lower():
        add(f"Bielefeld {clean}")
        add(f"Bi {clean}")

    replacements = [
        ("straße", "str"),
        ("Straße", "Str"),
        ("strasse", "str"),
        ("Strasse", "Str"),
        ("str.", "str"),
        ("Str.", "Str"),
    ]
    base_items = list(variants)
    for item in base_items:
        for old, new in replacements:
            if old in item:
                add(item.replace(old, new))

    return variants


def search_stations(query: str, limit: int = 12) -> list[Station]:
    found: dict[str, Station] = {}

    for term in _query_variants(query):
        url = SEARCH_BASE + urllib.parse.quote(term)
        try:
            data = _fetch_json(url)
        except Exception:
            continue

        for item in _collect_station_items(data):
            station_id = str(item.get("data", "")).strip()
            name = str(item.get("value", "")).strip()
            if not station_id or not name:
                continue
            found[station_id] = Station(station_id=station_id, name=name)

    stations = list(found.values())

    def score(station: Station) -> int:
        name = station.name.lower()
        points = 0
        if "bielefeld" in name or "bi-" in name:
            points += 100
        if station.station_id.startswith("230"):
            points += 50
        if "gellershagen" in name:
            points += 10
        q = query.lower()
        for part in q.replace(",", " ").split():
            if len(part) >= 4 and part in name:
                points += 4
        return -points

    stations.sort(key=score)
    return stations[:limit]


def get_departures(station_id: str, station_name: str, max_rows: int = 5) -> list[Departure]:
    payload = {
        "table[departure][stationId]": station_id,
        "table[departure][stationName]": station_name,
        "table[departure][platformVisibility]": "1",
        "table[departure][transport]": "0,1,2,3,4,5,15,6",
        "table[departure][useAllLines]": "1",
        "table[departure][linesFilter]": "",
        "table[departure][optimizedForStation]": "0",
        "table[departure][rowCount]": str(max_rows),
        "table[departure][refreshInterval]": "60",
        "table[departure][distance]": "0",
        "table[departure][marquee]": "-1",
        "table[sortBy]": "0",
    }

    data = _fetch_json(TABLE_URL, payload)
    raw_rows = data.get("departureData", []) if isinstance(data, dict) else []
    rows: list[Departure] = []

    for dep in raw_rows[:max_rows]:
        line = str(dep.get("lineNumber") or dep.get("name") or "-").strip()
        destination = str(dep.get("direction") or dep.get("route") or "-").strip()
        destination = destination.replace("Bielefeld,", "").replace("Bi-", "").strip()

        if len(destination) > 16:
            destination = destination[:15] + "…"

        countdown = dep.get("countdown", "?")
        try:
            mins_int = int(float(countdown))
            minutes = "jetzt" if mins_int <= 0 else f"{mins_int} min"
        except Exception:
            minutes = f"{countdown} min"

        rows.append(Departure(line=line, destination=destination, minutes=minutes))

    return rows
