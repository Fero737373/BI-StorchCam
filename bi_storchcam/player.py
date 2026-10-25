"""YouTube Music playback on the Pi itself: mpv plays, yt-dlp resolves the audio streams.

mpv runs idle in the background and is driven over its JSON IPC socket. The queue lives
here; yt-dlp turns each video ID into a stream URL with the YouTube Music session cookies
(Premium quality, no ads). Resolving takes a few seconds on a Pi, so the next track is
resolved in the background while the current one plays. Audio goes to PulseAudio/PipeWire,
which routes it to a connected Bluetooth speaker.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config_store import config_path
from .providers import ytmusic

LOGGER = logging.getLogger(__name__)
RESULT_TYPES = {"song", "video", "album", "playlist"}
QUEUE_LIMIT = 50
# Ab so vielen Sekunden springt „Zurück“ an den Anfang des Songs statt zum vorigen.
RESTART_SECONDS = 5

_lock = threading.RLock()
_queue: dict[str, Any] = {"tracks": [], "index": -1, "loading": False, "error": ""}
_urls: dict[str, tuple[str, float]] = {}
_mpv: dict[str, Any] = {"client": None}
_volume = {"value": 100}


class PlayerError(RuntimeError):
    pass


class MpvClient:
    """mpv im Leerlauf mit JSON-IPC; Antworten werden über request_id zugeordnet."""

    def __init__(self, on_event: Any) -> None:
        executable = shutil.which("mpv")
        if not executable:
            raise PlayerError("mpv ist nicht installiert")
        self._folder = tempfile.mkdtemp(prefix="storchcam-mpv.")
        path = os.path.join(self._folder, "ipc")
        self.process = subprocess.Popen(
            [executable, "--idle=yes", "--no-video", "--no-terminal", "--ao=pulse", "--audio-display=no",
             "--volume-max=100", f"--volume={_volume['value']}", "--ytdl=no", f"--input-ipc-server={path}"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        deadline = time.monotonic() + 5
        while not os.path.exists(path):
            if time.monotonic() > deadline or self.process.poll() is not None:
                self.close()
                raise PlayerError("mpv ließ sich nicht starten")
            time.sleep(0.05)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.connect(path)
        self._on_event = on_event
        self._pending: dict[int, dict[str, Any]] = {}
        self._next_id = 0
        self._write_lock = threading.Lock()
        threading.Thread(target=self._reader, name="mpv-ipc", daemon=True).start()

    def alive(self) -> bool:
        return self.process.poll() is None

    def _reader(self) -> None:
        buffer = b""
        while True:
            try:
                chunk = self._socket.recv(65536)
            except OSError:
                return
            if not chunk:
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if "request_id" in message and message["request_id"] in self._pending:
                    waiter = self._pending.pop(message["request_id"])
                    waiter["reply"] = message
                    waiter["event"].set()
                elif "event" in message:
                    self._on_event(message)

    def command(self, *arguments: Any, timeout: float = 5) -> Any:
        with self._write_lock:
            self._next_id += 1
            request_id = self._next_id
            waiter: dict[str, Any] = {"event": threading.Event()}
            self._pending[request_id] = waiter
            try:
                self._socket.sendall(json.dumps({"command": list(arguments), "request_id": request_id}).encode() + b"\n")
            except OSError as exc:
                raise PlayerError("mpv ist nicht erreichbar") from exc
        if not waiter["event"].wait(timeout):
            self._pending.pop(request_id, None)
            raise PlayerError("mpv antwortet nicht")
        reply = waiter["reply"]
        if reply.get("error") != "success":
            raise PlayerError(f"mpv: {reply.get('error')}")
        return reply.get("data")

    def get(self, name: str) -> Any:
        try:
            return self.command("get_property", name)
        except PlayerError:
            return None

    def close(self) -> None:
        try:
            self._socket.close()
        except (OSError, AttributeError):
            pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        shutil.rmtree(self._folder, ignore_errors=True)


def _client() -> MpvClient:
    with _lock:
        client = _mpv["client"]
        if client is None or not client.alive():
            if client:
                client.close()
            client = MpvClient(_on_mpv_event)
            _mpv["client"] = client
        return client


def _on_mpv_event(message: dict[str, Any]) -> None:
    # Nur ein natürliches Songende schaltet weiter; „stop“ kommt auch beim Laden des nächsten Songs.
    if message.get("event") == "end-file" and message.get("reason") in {"eof", "error"}:
        LOGGER.info("Song zu Ende (%s), nächster folgt", message.get("reason"))
        threading.Thread(target=_advance, args=(1,), name="player-next", daemon=True).start()


def cookie_file() -> Path:
    """Netscape-Cookiedatei für yt-dlp aus der YouTube-Music-Anmeldung, nur bei Änderung neu geschrieben."""
    target = config_path().parent / "ytmusic_cookies.txt"
    source = ytmusic.auth_path()
    if not source.is_file():
        raise PlayerError("YouTube Music ist nicht verbunden")
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    cookie = json.loads(source.read_text(encoding="utf-8")).get("cookie", "")
    lines = ["# Netscape HTTP Cookie File"]
    for part in str(cookie).split("; "):
        name, _, value = part.partition("=")
        if name:
            lines.append("\t".join([".youtube.com", "TRUE", "/", "TRUE", "2147483647", name, value]))
    fd, temporary = tempfile.mkstemp(prefix=".ytmusic_cookies.", dir=target.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return target


def _stream_url(video_id: str) -> str:
    cached = _urls.get(video_id)
    if cached and cached[1] - 600 > time.time():
        return cached[0]
    import yt_dlp  # type: ignore[import-untyped]  # erst hier: groß und nur zum Abspielen nötig

    options = {"format": "bestaudio/best", "quiet": True, "no_warnings": True, "noplaylist": True, "cookiefile": str(cookie_file())}
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
    except Exception as exc:  # yt-dlp wirft je nach Fehler sehr unterschiedliche Typen
        raise PlayerError(f"Song lässt sich nicht abspielen: {str(exc)[:160]}") from exc
    url = str(info["url"])
    expires = float(parse_qs(urlparse(url).query).get("expire", [time.time() + 3600])[0])
    _urls[video_id] = (url, expires)
    return url


def _prefetch(index: int) -> None:
    with _lock:
        tracks = _queue["tracks"]
        video_id = tracks[index]["videoId"] if 0 <= index < len(tracks) else ""
    if video_id:
        try:
            _stream_url(video_id)
        except PlayerError as exc:
            LOGGER.info("Nächsten Song nicht vorbereitet: %s", exc)


def _load(index: int) -> None:
    with _lock:
        tracks = _queue["tracks"]
        if not 0 <= index < len(tracks):
            return
        _queue.update({"index": index, "loading": True, "error": ""})
        video_id = tracks[index]["videoId"]
    try:
        url = _stream_url(video_id)
        client = _client()
        client.command("loadfile", url, "replace")
        client.command("set_property", "pause", False)
    except PlayerError as exc:
        with _lock:
            _queue["error"] = str(exc)
        LOGGER.warning("Wiedergabe fehlgeschlagen: %s", exc)
    finally:
        with _lock:
            _queue["loading"] = False
    threading.Thread(target=_prefetch, args=(index + 1,), name="player-prefetch", daemon=True).start()


def _advance(step: int) -> None:
    with _lock:
        target = _queue["index"] + step
        if not 0 <= target < len(_queue["tracks"]):
            return
    _load(target)


def _thumbnail(item: dict[str, Any]) -> str:
    thumbnails = item.get("thumbnails") or item.get("thumbnail") or []
    url = str(thumbnails[-1].get("url", "")) if isinstance(thumbnails, list) and thumbnails else ""
    return ytmusic.sized_cover(url)


def _seconds(item: dict[str, Any]) -> int:
    if item.get("duration_seconds"):
        return int(item["duration_seconds"])
    text = str(item.get("length") or item.get("duration") or "")
    try:
        parts = [int(part) for part in text.split(":")]
    except ValueError:
        return 0
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def _track(item: dict[str, Any], cover: str = "") -> dict[str, Any]:
    artists = ", ".join(str(a.get("name", "")) for a in item.get("artists") or [] if isinstance(a, dict))
    return {
        "videoId": str(item.get("videoId", "")),
        "title": str(item.get("title", "")),
        "artist": artists,
        "cover": _thumbnail(item) or cover,
        "duration": _seconds(item),
    }


def search(query: str) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        return []
    try:
        results = ytmusic.api().search(query, limit=20)
    except Exception as exc:  # ytmusicapi wirft je nach Fehler sehr unterschiedliche Typen
        raise PlayerError(f"Suche fehlgeschlagen: {str(exc)[:160]}") from exc
    found = []
    for item in results:
        kind = item.get("resultType")
        if kind not in RESULT_TYPES:
            continue
        identifier = item.get("videoId") if kind in {"song", "video"} else item.get("browseId") if kind == "album" else item.get("playlistId") or item.get("browseId")
        if not identifier:
            continue
        artists = ", ".join(str(a.get("name", "")) for a in item.get("artists") or [] if isinstance(a, dict))
        found.append({
            "kind": kind,
            "id": str(identifier),
            "title": str(item.get("title") or ""),
            "subtitle": artists or str(item.get("author") or ""),
            "cover": _thumbnail(item),
        })
    return found


def my_playlists() -> list[dict[str, Any]]:
    """Playlists aus der eigenen YouTube-Music-Bibliothek (inklusive „Liked Music“)."""
    try:
        items = ytmusic.api().get_library_playlists(limit=50)
    except Exception as exc:  # ytmusicapi wirft je nach Fehler sehr unterschiedliche Typen
        raise PlayerError(f"Playlists nicht abrufbar: {str(exc)[:160]}") from exc
    found = []
    for item in items or []:
        if not isinstance(item, dict) or not item.get("playlistId"):
            continue
        count = item.get("count")
        found.append({
            "kind": "playlist",
            "id": str(item["playlistId"]),
            "title": str(item.get("title") or ""),
            "subtitle": f"{count} Songs" if count not in (None, "") else "",
            "cover": _thumbnail(item),
        })
    return found


def _tracks_for(kind: str, identifier: str) -> list[dict[str, Any]]:
    api = ytmusic.api()
    if kind in {"song", "video"}:
        # Wie in der App: nach dem Song läuft das passende „Radio“ weiter.
        watch = api.get_watch_playlist(videoId=identifier, limit=QUEUE_LIMIT)
        tracks = [_track(item) for item in watch.get("tracks") or [] if isinstance(item, dict)]
        if not tracks or tracks[0]["videoId"] != identifier:
            tracks.insert(0, {"videoId": identifier, "title": "", "artist": "", "cover": "", "duration": 0})
        return tracks
    if kind == "album":
        album = api.get_album(identifier)
        cover = _thumbnail(album)
        return [_track(item, cover) for item in album.get("tracks") or []]
    playlist = api.get_playlist(identifier.removeprefix("VL"), limit=QUEUE_LIMIT)
    return [_track(item) for item in playlist.get("tracks") or []]


def full_output_volume(wait_for_bluetooth: float = 0) -> None:
    """Stellt den Lautsprecher des Pi (PipeWire/Pulse) auf 100 %; leiser gestellt wird nur noch im Player.

    Bluetooth-Lautsprecher starten in PipeWire oft bei 40 %, was dort rund -24 dB bedeutet. Nach dem
    Verbinden erscheint der Lautsprecher erst nach ein paar Sekunden als Ausgabe, darum kann gewartet werden.
    """
    pactl = shutil.which("pactl")
    if not pactl:
        return
    deadline = time.monotonic() + wait_for_bluetooth
    try:
        while time.monotonic() < deadline:
            sink = subprocess.run([pactl, "get-default-sink"], capture_output=True, text=True, timeout=5, check=False).stdout
            if "bluez" in sink:
                break
            time.sleep(1)
        subprocess.run([pactl, "set-sink-volume", "@DEFAULT_SINK@", "100%"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOGGER.warning("Lautstärke des Lautsprechers nicht gesetzt: %s", exc)


def play(kind: str, identifier: str) -> None:
    if kind not in RESULT_TYPES or not identifier:
        raise PlayerError("Unbekannter Eintrag")
    try:
        tracks = [track for track in _tracks_for(kind, identifier) if track["videoId"]][:QUEUE_LIMIT]
    except PlayerError:
        raise
    except Exception as exc:  # ytmusicapi wirft je nach Fehler sehr unterschiedliche Typen
        raise PlayerError(f"Titel nicht gefunden: {str(exc)[:160]}") from exc
    if not tracks:
        raise PlayerError("Keine abspielbaren Songs gefunden")
    with _lock:
        _queue.update({"tracks": tracks, "index": 0, "loading": True, "error": ""})
    threading.Thread(target=_load, args=(0,), name="player-load", daemon=True).start()


def _active_client() -> MpvClient:
    with _lock:
        client = _mpv["client"]
    if client is None or not client.alive() or not _queue["tracks"]:
        raise PlayerError("Auf dem Pi läuft gerade nichts")
    return client


def control(action: str, value: Any = None) -> None:
    if action == "volume":
        try:
            volume = max(0, min(100, int(value)))
        except (TypeError, ValueError) as exc:
            raise PlayerError("Ungültige Lautstärke") from exc
        _volume["value"] = volume
        with _lock:
            client = _mpv["client"]
        if client and client.alive():
            client.command("set_property", "volume", volume)
        return
    client = _active_client()
    if action == "toggle":
        client.command("cycle", "pause")
    elif action == "next":
        threading.Thread(target=_advance, args=(1,), name="player-next", daemon=True).start()
    elif action == "previous":
        if float(client.get("time-pos") or 0) > RESTART_SECONDS or _queue["index"] <= 0:
            client.command("seek", 0, "absolute")
        else:
            threading.Thread(target=_advance, args=(-1,), name="player-previous", daemon=True).start()
    elif action == "stop":
        client.command("stop")
        with _lock:
            _queue.update({"tracks": [], "index": -1})
    else:
        raise PlayerError("Unbekannte Aktion")


def now_playing() -> dict[str, Any] | None:
    """Was mpv gerade spielt (oder pausiert), als Musikanzeige; None, wenn der Pi nichts abspielt."""
    with _lock:
        tracks, index, loading, error = _queue["tracks"], _queue["index"], _queue["loading"], _queue["error"]
        client = _mpv["client"]
    if not 0 <= index < len(tracks):
        return None
    track = tracks[index]
    running = bool(client and client.alive())
    if running and not loading and client.get("idle-active"):
        return None  # Warteschlange zu Ende gespielt
    paused = bool(client.get("pause")) if running else True
    position = client.get("time-pos") if running and not loading else 0
    duration = client.get("duration") if running and not loading else track["duration"]
    return {
        "source": "ytmusic",
        "device": "pi",
        "title": track["title"] or "Wird geladen …",
        "artist": track["artist"],
        "album": "",
        "cover": track["cover"],
        "progress_ms": int(float(position or 0) * 1000),
        "duration_ms": int(float(duration or track["duration"] or 0) * 1000),
        "paused": paused or loading,
        "loading": loading,
        "error": error,
        "volume": _volume["value"],
        "fetched_at": int(time.time() * 1000),
    }


def shutdown() -> None:
    with _lock:
        client = _mpv["client"]
        _mpv["client"] = None
        _queue.update({"tracks": [], "index": -1})
    if client:
        client.close()
