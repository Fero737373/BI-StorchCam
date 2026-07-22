"""VRR departure provider with complete configuration-aware caching."""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from ..version import __version__

LOGGER = logging.getLogger(__name__)
SEARCH_URL = "https://haltestellenmonitor.vrr.de/backend/api/stations/search"
TABLE_URL = "https://haltestellenmonitor.vrr.de/backend/api/stations/table"
_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()


def _fetch_json(url: str, data: dict[str, Any] | None = None, timeout: int = 12) -> dict[str, Any]:
    headers = {"User-Agent": f"BI-StorchCam/{__version__}", "Accept": "application/json,text/plain,*/*"}
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8") if data is not None else None,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8", "replace"))
    if not isinstance(result, dict):
        raise ValueError("VRR lieferte kein JSON-Objekt")
    return result


def search_station(query: str) -> list[dict[str, str]]:
    clean = query.strip()
    if len(clean) < 2:
        return []
    data = _fetch_json(SEARCH_URL + "?query=" + urllib.parse.quote(clean))
    results: list[dict[str, str]] = []
    for item in data.get("suggestions", [])[:12]:
        if not isinstance(item, dict):
            continue
        station_id = str(item.get("data", "")).strip()
        station_name = str(item.get("value", "")).strip()
        if station_id and station_name:
            results.append({"station_id": station_id, "station_name": station_name})
    return results


def cache_key(config: dict[str, Any]) -> str:
    transit = config.get("transit", {})
    relevant = {
        "provider": transit.get("provider"),
        "refresh_seconds": transit.get("refresh_seconds"),
        "default_max_rows": transit.get("default_max_rows"),
        "target_len": transit.get("target_len"),
        "stops": transit.get("stops", []),
    }
    return json.dumps(relevant, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _matches_line(line: str, filters: list[str], nightbus_only: bool) -> bool:
    candidate = line.upper().strip()
    if nightbus_only and not candidate.startswith("N"):
        return False
    wanted = {item.upper().strip() for item in filters if item.strip()}
    return not wanted or candidate in wanted or ("N" in wanted and candidate.startswith("N"))


def _format_minutes(value: Any) -> str:
    try:
        minutes = int(float(value))
    except (TypeError, ValueError):
        return "–"
    if minutes <= 0:
        return "jetzt"
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60}h {minutes % 60:02d}"


def _board(stop: dict[str, Any], default_max: int, target_len: int) -> dict[str, Any]:
    station_id = str(stop.get("station_id", "")).strip()
    station_name = str(stop.get("station_name", "")).strip()
    if not station_id:
        matches = search_station(station_name)
        if not matches:
            raise ValueError(f"Haltestelle nicht gefunden: {station_name}")
        station_id = matches[0]["station_id"]
        station_name = matches[0]["station_name"]
    payload = {
        "table[departure][stationId]": station_id,
        "table[departure][stationName]": station_name,
        "table[departure][platformVisibility]": "1",
        "table[departure][transport]": "0,1,2,3,4,5,15,6",
        "table[departure][useAllLines]": "1",
        "table[departure][linesFilter]": "",
        "table[departure][optimizedForStation]": "0",
        "table[departure][rowCount]": "40",
        "table[departure][refreshInterval]": "60",
        "table[departure][distance]": "0",
        "table[departure][marquee]": "-1",
        "table[sortBy]": "0",
    }
    data = _fetch_json(TABLE_URL, payload)
    filters = [str(item) for item in stop.get("line_filter", [])]
    nightbus = bool(stop.get("nightbus_only", False))
    limit = int(stop.get("max_rows") or default_max)
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for departure in data.get("departureData", []):
        if not isinstance(departure, dict):
            continue
        line = str(departure.get("lineNumber") or departure.get("name") or "–").strip()
        if not _matches_line(line, filters, nightbus):
            continue
        target = str(departure.get("direction") or departure.get("route") or "–").strip()
        target = target.replace("Bielefeld,", "").replace("Bi-", "").strip()
        key = (line.casefold(), target.casefold())
        if key in seen:
            continue
        seen.add(key)
        if len(target) > target_len:
            target = target[: target_len - 1].rstrip() + "…"
        rows.append({"line": line, "target": target, "mins": _format_minutes(departure.get("countdown"))})
        if len(rows) >= limit:
            break
    title = str(stop.get("title") or station_name).replace("Bielefeld", "").strip(" ,") or "Haltestelle"
    return {
        "title": title,
        "station_id": station_id,
        "station_name": station_name,
        "rows": rows,
        "hide_if_empty": bool(stop.get("hide_if_empty", True)),
        "ok": True,
    }


def get_boards(config: dict[str, Any], *, force: bool = False) -> list[dict[str, Any]]:
    transit = config.get("transit", {})
    key = cache_key(config)
    refresh = int(transit.get("refresh_seconds", 60))
    now = time.monotonic()
    with _cache_lock:
        cached = copy.deepcopy(_cache.get(key))
    if cached and not force and now - float(cached.get("cached_at", 0)) < refresh:
        return cached["boards"]

    boards: list[dict[str, Any]] = []
    for stop in transit.get("stops", []):
        try:
            board = _board(stop, int(transit.get("default_max_rows", 2)), int(transit.get("target_len", 16)))
        except Exception as exc:
            LOGGER.warning("VRR-Abfrage für %s fehlgeschlagen: %s", stop.get("station_name"), exc)
            board = {
                "title": str(stop.get("title") or stop.get("station_name") or "Haltestelle"),
                "station_id": str(stop.get("station_id", "")),
                "station_name": str(stop.get("station_name", "")),
                "rows": [],
                "hide_if_empty": bool(stop.get("hide_if_empty", True)),
                "ok": False,
                "error": str(exc)[:160],
            }
        if board["rows"] or not board["hide_if_empty"] or not board["ok"]:
            boards.append(board)
    with _cache_lock:
        _cache[key] = {"cached_at": now, "boards": copy.deepcopy(boards)}
    return boards


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
