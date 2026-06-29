# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from typing import Any


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass


def prepare_display(config: dict[str, Any]) -> dict[str, str]:
    kiosk = config.get("kiosk", {})
    screen = config.get("screen", {})
    env = os.environ.copy()
    env["DISPLAY"] = str(kiosk.get("display", ":0"))
    env["XAUTHORITY"] = os.path.expanduser(str(kiosk.get("xauthority", "~/.Xauthority")))

    output = str(screen.get("output", "DSI-2"))
    rotation = str(screen.get("rotation", "right"))
    if output and rotation and rotation != "none":
        _run(["xrandr", "--output", output, "--rotate", rotation], env=env)

    matrix = str(screen.get("touch_matrix", "")).strip()
    if matrix:
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


def start_browser(config: dict[str, Any], url: str) -> subprocess.Popen | None:
    kiosk = config.get("kiosk", {})
    env = prepare_display(config)

    browser = str(kiosk.get("browser", "chromium"))
    browser_bin = shutil.which(browser) or shutil.which("chromium-browser") or shutil.which("chromium")
    if not browser_bin:
        print("FEHLER: Chromium nicht gefunden.")
        return None

    if kiosk.get("kill_existing_chromium", True):
        _run(["pkill", "-f", "storchcam-profile"], env=env)

    flags = [
        browser_bin,
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--autoplay-policy=no-user-gesture-required",
        "--disable-features=TranslateUI,MediaRouter",
        f"--user-data-dir={kiosk.get('profile_dir', '/tmp/storchcam-profile')}",
    ]
    if not kiosk.get("use_gpu", True):
        flags.extend(["--disable-gpu", "--disable-gpu-compositing"])
    flags.extend(str(x) for x in kiosk.get("extra_flags", []))
    flags.append(url)

    print("Starte Chromium:", " ".join(shlex.quote(x) for x in flags))
    return subprocess.Popen(flags, env=env)
