from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional


def _windows_browser_candidates() -> list[str]:
    candidates = []
    for env in ["PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"]:
        root = os.environ.get(env)
        if not root:
            continue
        candidates.extend([
            str(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"),
            str(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
        ])
    return candidates


def find_browser() -> Optional[str]:
    custom = os.environ.get("BI_STORCHCAM_BROWSER")
    if custom and Path(custom).exists():
        return custom

    names = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "microsoft-edge",
        "msedge",
        "chrome",
    ]

    for name in names:
        path = shutil.which(name)
        if path:
            return path

    if platform.system().lower() == "windows":
        for candidate in _windows_browser_candidates():
            if Path(candidate).exists():
                return candidate

    return None


def launch_stream(url: str, fullscreen: bool = True) -> Optional[subprocess.Popen]:
    browser = find_browser()
    if not browser:
        webbrowser.open(url)
        return None

    args = [browser]

    if fullscreen:
        args.extend([
            "--start-fullscreen",
            "--noerrdialogs",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--autoplay-policy=no-user-gesture-required",
        ])

    args.append(url)

    try:
        return subprocess.Popen(args)
    except Exception:
        webbrowser.open(url)
        return None
