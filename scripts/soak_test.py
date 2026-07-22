#!/usr/bin/env python3
"""Monitor a running Raspberry-Pi kiosk and optionally crash its explicit browser PID."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("API-Antwort ist kein Objekt")
    return value


def rss_mb(pid: int | None) -> float | None:
    if not pid:
        return None
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 2)
    except (OSError, ValueError, IndexError):
        return None
    return None


def process_command(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return ""


def browser_pids() -> list[int]:
    found: list[int] = []
    proc = Path("/proc")
    if not proc.exists():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        command = process_command(int(entry.name)).lower()
        if any(name in command for name in ("chromium", "google-chrome", "microsoft-edge", "msedge")) and "bi-storchcam" in command:
            found.append(int(entry.name))
    return found


def validate_browser_pid(pid: int) -> None:
    command = process_command(pid).lower()
    if not any(name in command for name in ("chromium", "google-chrome", "microsoft-edge", "msedge")):
        raise SystemExit(f"PID {pid} ist kein erkannter Browserprozess; Abbruch ohne Signal")


def log_sizes(cache: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for base in ("storchcam.log", "chromium.log"):
        for candidate in cache.glob(f"{base}*"):
            if candidate.is_file():
                result[candidate.name] = candidate.stat().st_size
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="BI-StorchCam Soak-Test")
    parser.add_argument("--hours", type=float, default=8)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--app-pid", type=int)
    parser.add_argument("--browser-pid", type=int)
    parser.add_argument("--simulate-browser-crash-after", type=float, help="Sekunden bis SIGTERM an die explizite Browser-PID")
    args = parser.parse_args()
    if args.simulate_browser_crash_after is not None and not args.browser_pid:
        parser.error("--simulate-browser-crash-after erfordert --browser-pid")
    if args.browser_pid:
        validate_browser_pid(args.browser_pid)

    cache = Path(os.path.expanduser("~/.cache/BI-StorchCam"))
    cache.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + max(0.01, args.hours) * 3600
    killed = False
    health_failures: list[str] = []
    state_stamps: set[str] = set()
    memory: list[float] = []
    provider_failures_observed: set[str] = set()
    restart_observed = False

    while time.monotonic() < deadline:
        elapsed = time.monotonic() - started
        try:
            health = fetch_json(f"http://{args.host}:{args.port}/api/health")
            if not health.get("ok") or not health.get("state_ready"):
                health_failures.append(f"{elapsed:.0f}s: nicht bereit")
            state = fetch_json(f"http://{args.host}:{args.port}/api/state")
            if state.get("generated_at"):
                state_stamps.add(str(state["generated_at"]))
            for name in ("weather", "radar"):
                value = state.get(name)
                if isinstance(value, dict) and value.get("ok") is False:
                    provider_failures_observed.add(name)
            for board in state.get("boards", []):
                if isinstance(board, dict) and board.get("ok") is False:
                    provider_failures_observed.add("transit")
        except Exception as exc:
            health_failures.append(f"{elapsed:.0f}s: {exc}")
        current_rss = rss_mb(args.app_pid)
        if current_rss is not None:
            memory.append(current_rss)
        if args.browser_pid and args.simulate_browser_crash_after is not None and not killed and elapsed >= args.simulate_browser_crash_after:
            os.kill(args.browser_pid, signal.SIGTERM)
            killed = True
        if killed and any(pid != args.browser_pid for pid in browser_pids()):
            restart_observed = True
        time.sleep(max(1, args.interval))

    growth = (memory[-1] - memory[0]) if len(memory) >= 2 else None
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_hours": args.hours,
        "health_failures": health_failures,
        "unique_state_timestamps": len(state_stamps),
        "rss_samples_mb": memory,
        "rss_growth_mb": growth,
        "provider_offline_states_observed": sorted(provider_failures_observed),
        "browser_crash_sent": killed,
        "browser_restart_observed": restart_observed,
        "log_sizes_bytes": log_sizes(cache),
    }
    report["passed"] = (
        not health_failures
        and len(state_stamps) >= 2
        and (growth is None or growth < 150)
        and (not killed or restart_observed)
    )
    target = cache / f"soak-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Bericht: {target}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
