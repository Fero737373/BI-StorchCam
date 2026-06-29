# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

SEARCH_URL = "https://haltestellenmonitor.vrr.de/backend/api/stations/search"
TABLE_URL = "https://haltestellenmonitor.vrr.de/backend/api/stations/table"

_cache: dict[str, Any] = {"ts": 0.0, "boards": []}


def _fetch_json(url: str, data: dict[str, Any] | None = None, timeout: int = 12) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 BI-StorchCam/2.0", "Accept": "application/json,text/plain,*/*"}
    if data is None:
        req = urllib.request.Request(url, headers=headers)
    else:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def search_station(query: str) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    url = SEARCH_URL + "?query=" + urllib.parse.quote(query.strip())
    data = _fetch_json(url)
    out = []
    for item in data.get("suggestions", [])[:10]:
        out.append({"station_id": str(item.get("data", "")), "station_name": str(item.get("value", ""))})
    return out


def _fmt_mins(value: Any) -> str:
    try:
        mins = int(float(value))
    except Exception:
        return f"{value} min"
    if mins <= 0:
        return "jetzt"
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h}h {m} min" if m else f"{h}h"


def _matches_line(line: str, filters: list[str], nightbus_only: bool) -> bool:
    line_up = line.upper().strip()
    if nightbus_only and not line_up.startswith("N"):
        return False
    if not filters:
        return True
    for f in filters:
        f_up = str(f).upper().strip()
        if not f_up:
            continue
        if f_up == "N" and line_up.startswith("N"):
            return True
        if line_up == f_up:
            return True
    return False


def _departures_for_stop(stop: dict[str, Any], default_max_rows: int, target_len: int) -> list[dict[str, str]]:
    station_id = str(stop.get("station_id") or "").strip()
    station_name = str(stop.get("station_name") or "").strip()
    if not station_id and station_name:
        found = search_station(station_name)
        station_id = found[0]["station_id"] if found else ""
        if not station_name and found:
            station_name = found[0]["station_name"]
    if not station_id:
        return []

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
    filters = [str(x) for x in stop.get("line_filter", [])]
    nightbus_only = bool(stop.get("nightbus_only", False))
    max_rows = int(stop.get("max_rows") or default_max_rows)

    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for dep in data.get("departureData", []):
        line = str(dep.get("lineNumber") or dep.get("name") or "-").strip()
        if not _matches_line(line, filters, nightbus_only):
            continue
        raw_target = str(dep.get("direction") or dep.get("route") or "-").strip()
        key = f"{line}|{raw_target.lower()}"
        if key in seen:
            continue
        seen.add(key)
        target = raw_target.replace("Bielefeld,", "").replace("Bi-", "").strip()
        if len(target) > target_len:
            target = target[: max(1, target_len - 1)] + "…"
        rows.append({"line": line, "target": target, "mins": _fmt_mins(dep.get("countdown", "?"))})
        if len(rows) >= max_rows:
            break
    return rows


def get_boards(config: dict[str, Any]) -> list[dict[str, Any]]:
    transit = config.get("transit", {})
    refresh = int(transit.get("refresh_seconds", 60))
    now = time.time()
    if now - float(_cache.get("ts", 0)) < refresh:
        return list(_cache.get("boards", []))

    boards = []
    default_max = int(transit.get("default_max_rows", 2))
    target_len = int(transit.get("target_len", 16))
    for stop in transit.get("stops", []):
        title = str(stop.get("title") or stop.get("station_name") or "HALT").upper()
        try:
            rows = _departures_for_stop(stop, default_max, target_len)
        except Exception as exc:
            rows = []
            stop["last_error"] = str(exc)
        if stop.get("hide_if_empty", False) and not rows:
            continue
        boards.append({"title": title, "rows": rows, "hide_if_empty": bool(stop.get("hide_if_empty", False))})

    _cache["ts"] = now
    _cache["boards"] = boards
    return list(boards)
