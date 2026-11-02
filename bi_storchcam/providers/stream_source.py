"""Resolve the configured live stream for the kiosk's own video player.

YouTube addresses become an HLS playlist through yt-dlp, direct ``.m3u8`` addresses are used as they
are, and everything else stays an embedded web page as before. Resolved YouTube playlists expire after
a few hours; the cache drops them ten minutes early so the player never asks for a dead address.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

LOGGER = logging.getLogger(__name__)
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
EXPIRE_IN_PATH = re.compile(r"/expire/(\d+)")
DEFAULT_LIFETIME = 3 * 3600
REFRESH_MARGIN = 600
QUALITIES = {"auto": 1080, "1080": 1080, "720": 720, "480": 480}
YOUTUBE_HOSTS = {"youtube.com", "youtube-nocookie.com", "music.youtube.com"}

_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()
# yt-dlp braucht auf dem Pi einige Sekunden; gleichzeitige Anfragen warten auf dasselbe Ergebnis.
_resolve_lock = threading.Lock()


class StreamError(RuntimeError):
    """User-facing reason why a stream cannot play in the own player."""


def youtube_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    parts = [part for part in parsed.path.split("/") if part]
    candidate = ""
    if host == "youtu.be" and parts:
        candidate = parts[0]
    elif host in YOUTUBE_HOSTS and parts:
        if parts[0] == "watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parts[0] in {"embed", "live", "shorts"} and len(parts) > 1:
            candidate = parts[1]
    return candidate if VIDEO_ID.fullmatch(candidate) else ""


def is_hls(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and parsed.path.lower().endswith(".m3u8")


def max_height(quality: Any) -> int:
    return QUALITIES.get(str(quality), QUALITIES["auto"])


def expires_at(url: str, now: float) -> float:
    """googlevideo-Adressen tragen ihr Ablaufdatum im Pfad (``/expire/<unix>/``) oder als Parameter."""
    parsed = urlparse(url)
    match = EXPIRE_IN_PATH.search(parsed.path)
    raw = match.group(1) if match else parse_qs(parsed.query).get("expire", [""])[0]
    try:
        return float(raw)
    except ValueError:
        return now + DEFAULT_LIFETIME


def _hls_address(info: dict[str, Any]) -> str:
    # Die Master-Playlist enthält alle Qualitäten; hls.js wählt daraus passend zur Leitung.
    if info.get("manifest_url"):
        return str(info["manifest_url"])
    if str(info.get("protocol", "")).startswith("m3u8") and info.get("url"):
        return str(info["url"])
    for fmt in info.get("formats") or []:
        if isinstance(fmt, dict) and str(fmt.get("protocol", "")).startswith("m3u8"):
            return str(fmt.get("manifest_url") or fmt.get("url") or "")
    return ""


def _youtube_playlist(video_id: str) -> dict[str, Any]:
    import yt_dlp  # type: ignore[import-untyped]  # erst hier laden: groß und nur für YouTube nötig

    options = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True, "format": "best[protocol^=m3u8]/best"}
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    except Exception as exc:  # yt-dlp wirft je nach Fehler sehr unterschiedliche Typen
        raise StreamError(f"YouTube liefert keinen Stream: {str(exc)[:160]}") from exc
    if not isinstance(info, dict):
        raise StreamError("YouTube liefert keine Streamdaten")
    playlist = _hls_address(info)
    if not playlist:
        raise StreamError("Kein HLS-Livestream; das Video läuft eingebettet")
    return {
        "upstream": playlist,
        "title": str(info.get("title") or ""),
        "channel": str(info.get("channel") or info.get("uploader") or ""),
        "live": bool(info.get("is_live")),
    }


def resolve(url: str, *, refresh: bool = False, now: float | None = None) -> dict[str, Any]:
    """``{"kind": "hls", "upstream", "expires", ...}``, ``{"kind": "embed", "reason"}`` oder ``{"kind": "none"}``."""
    clean = url.strip()
    if not clean:
        return {"kind": "none"}
    current = time.time() if now is None else now
    if is_hls(clean):
        return {"kind": "hls", "upstream": clean, "expires": current + DEFAULT_LIFETIME, "title": "", "channel": "", "live": True}
    video_id = youtube_id(clean)
    if not video_id:
        return {"kind": "embed", "reason": "Diese Adresse ist weder YouTube noch HLS und wird eingebettet"}
    with _resolve_lock:
        with _cache_lock:
            cached = _cache.get(video_id)
        if cached and not refresh and cached["expires"] - REFRESH_MARGIN > current:
            return dict(cached)
        try:
            result: dict[str, Any] = {"kind": "hls", **_youtube_playlist(video_id)}
        except StreamError as exc:
            LOGGER.warning("Stream %s läuft eingebettet: %s", video_id, exc)
            return {"kind": "embed", "reason": str(exc)}
        result["expires"] = expires_at(result["upstream"], current)
        with _cache_lock:
            _cache[video_id] = dict(result)
    LOGGER.info("Stream %s im eigenen Player, gültig bis %s", video_id, time.strftime("%H:%M", time.localtime(result["expires"])))
    return result


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
