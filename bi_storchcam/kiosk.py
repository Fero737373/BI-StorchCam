# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


def _is_windows() -> bool:
    return os.name == "nt"


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    if not cmd or not shutil.which(cmd[0]):
        return
    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass


def _default_profile_dir() -> str:
    if _is_windows():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return str(Path(base) / "BI-StorchCam" / "browser-profile")
    return "/tmp/storchcam-profile"


def _browser_log_path(config: dict[str, Any]) -> Path:
    kiosk = config.get("kiosk", {})
    raw = str(kiosk.get("log_file") or "~/.cache/BI-StorchCam/chromium.log")
    return Path(os.path.expandvars(os.path.expanduser(raw)))


def _browser_candidates(configured: str) -> list[str]:
    configured = (configured or "").strip()
    candidates: list[str] = []

    if configured and configured.lower() not in {"auto", "default"}:
        candidates.append(configured)

    if _is_windows():
        program_files = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        for base in [x for x in program_files if x]:
            candidates.extend(
                [
                    str(Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                    str(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                    str(Path(base) / "Chromium" / "Application" / "chrome.exe"),
                ]
            )
        candidates.extend(["msedge", "chrome", "chromium"])
    else:
        candidates.extend(
            [
                "chromium-browser",
                "chromium",
                "google-chrome-stable",
                "google-chrome",
                "microsoft-edge",
                "brave-browser",
                "firefox",
            ]
        )

    seen: set[str] = set()
    out: list[str] = []
    for item in candidates:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _resolve_browser(configured: str) -> str | None:
    for candidate in _browser_candidates(configured):
        expanded = os.path.expandvars(os.path.expanduser(candidate))
        if os.path.isabs(expanded) or "\\" in expanded or "/" in expanded:
            if Path(expanded).exists():
                return expanded
            continue
        found = shutil.which(expanded)
        if found:
            return found
    return None


def _clear_profile_locks(profile_dir: str) -> None:
    profile = Path(profile_dir)
    for name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
        try:
            (profile / name).unlink(missing_ok=True)
        except OSError:
            pass


def prepare_display(config: dict[str, Any]) -> dict[str, str]:
    """Prepare Linux/X11 display helpers.

    Windows does not have xrandr/xinput/xset. Skipping this whole block there
    prevents noisy terminal errors while keeping Raspberry Pi behaviour intact.
    """
    env = os.environ.copy()
    if _is_windows():
        return env

    kiosk = config.get("kiosk", {})
    screen = config.get("screen", {})

    display = str(kiosk.get("display", ":0")).strip()
    if display:
        env["DISPLAY"] = display

    xauthority = str(kiosk.get("xauthority", "~/.Xauthority")).strip()
    if xauthority:
        env["XAUTHORITY"] = os.path.expanduser(xauthority)

    output = str(screen.get("output", "DSI-2")).strip()
    rotation = str(screen.get("rotation", "right")).strip()
    if output and rotation and rotation != "none":
        _run(["xrandr", "--output", output, "--rotate", rotation], env=env)

    matrix = str(screen.get("touch_matrix", "")).strip()
    if matrix and shutil.which("xinput"):
        try:
            ids = subprocess.check_output(["xinput", "list", "--id-only"], env=env, text=True, timeout=3).splitlines()
            for dev_id in ids:
                name = subprocess.check_output(["xinput", "list", "--name-only", dev_id], env=env, text=True, timeout=3)
                props = subprocess.check_output(["xinput", "list-props", dev_id], env=env, text=True, timeout=3)
                blob = f"{name} {props}".lower()
                if any(x in blob for x in ("touch", "touchscreen", "goodix", "ft5406")) and "coordinate transformation matrix" in props.lower():
                    _run(["xinput", "set-prop", dev_id, "Coordinate Transformation Matrix", *matrix.split()], env=env)
        except Exception:
            pass

    if kiosk.get("disable_screensaver", True):
        for cmd in (["xset", "s", "off"], ["xset", "-dpms"], ["xset", "s", "noblank"], ["xset", "dpms", "force", "on"]):
            _run(list(cmd), env=env)

    return env


def browser_is_running(process: subprocess.Popen[Any] | None) -> bool:
    return process is not None and process.poll() is None


def stop_browser(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    except Exception:
        pass


def start_browser(config: dict[str, Any], url: str) -> subprocess.Popen[Any] | None:
    kiosk = config.get("kiosk", {})
    env = prepare_display(config)

    configured = str(kiosk.get("browser", "auto"))
    browser_bin = _resolve_browser(configured)

    if not browser_bin:
        print("WARNUNG: Kein Chromium/Chrome/Edge gefunden. Öffne URL im Standardbrowser.")
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f"FEHLER: Browser konnte nicht geöffnet werden: {exc}")
        return None

    if kiosk.get("kill_existing_chromium", True) and not _is_windows():
        _run(["pkill", "-f", "storchcam-profile"], env=env)

    profile_dir = str(kiosk.get("profile_dir") or "").strip()
    if not profile_dir or (_is_windows() and profile_dir.startswith("/tmp/")):
        profile_dir = _default_profile_dir()
    profile_dir = os.path.expandvars(os.path.expanduser(profile_dir))
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    _clear_profile_locks(profile_dir)

    flags = [
        browser_bin,
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
        "--password-store=basic",
        "--autoplay-policy=no-user-gesture-required",
        "--disable-features=TranslateUI,MediaRouter",
        f"--user-data-dir={profile_dir}",
    ]
    if not _is_windows():
        flags.append("--ozone-platform=x11")
    if not kiosk.get("use_gpu", True):
        flags.extend(["--disable-gpu", "--disable-gpu-compositing"])
    flags.extend(str(x) for x in kiosk.get("extra_flags", []))
    flags.append(url)

    log_path = _browser_log_path(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    command = " ".join(shlex.quote(x) for x in flags)
    print(f"Starte Browser: {command}")
    print(f"Chromium-Log: {log_path}")

    try:
        with log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"\n===== Chromium start {timestamp} =====\n{command}\n")
            log_handle.flush()
            return subprocess.Popen(
                flags,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=not _is_windows(),
            )
    except Exception as exc:
        print(f"FEHLER: Browserstart fehlgeschlagen: {exc}")
        try:
            with log_path.open("a", encoding="utf-8") as log_handle:
                log_handle.write(f"Browserstart fehlgeschlagen: {exc}\n")
        except OSError:
            pass
        return None
