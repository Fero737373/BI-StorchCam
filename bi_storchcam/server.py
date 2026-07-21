"""Hardened local HTTP server for static UI, snapshots and authenticated config."""

from __future__ import annotations

import copy
import ipaddress
import json
import logging
import mimetypes
import sys
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .admin import SessionStore, hash_pin, verify_pin
from .config_store import ConfigError, config_path, public_config, save_config, validate_config
from .providers.transit_vrr_smart import search_station
from .state import StateManager
from .version import __version__

LOGGER = logging.getLogger(__name__)


def web_directory() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "bi_storchcam" / "web"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "web"


@dataclass
class ServerContext:
    config: dict[str, Any]
    state: StateManager
    started_at: float = field(default_factory=time.monotonic)
    lock: threading.RLock = field(default_factory=threading.RLock)
    sessions: SessionStore = field(init=False)

    def __post_init__(self) -> None:
        ttl = int(self.config.get("server", {}).get("admin_session_minutes", 30)) * 60
        self.sessions = SessionStore(ttl)

    def get_config(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.config)

    def replace_config(self, config: dict[str, Any]) -> None:
        with self.lock:
            self.config = copy.deepcopy(config)
        self.state.update_config(config)


class StorchServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], context: ServerContext) -> None:
        self.context = context
        super().__init__(address, StorchHandler)


class RequestError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


class StorchHandler(BaseHTTPRequestHandler):
    server_version = f"BI-StorchCam/{__version__}"
    sys_version = ""

    @property
    def context(self) -> ServerContext:
        return self.server.context  # type: ignore[attr-defined]

    def _config(self) -> dict[str, Any]:
        return self.context.get_config()

    def _security_headers(self) -> None:
        config = self._config()
        stream_url = str(config.get("stream", {}).get("url", ""))
        frame_origin = ""
        parsed = urlparse(stream_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            frame_origin = f" {parsed.scheme}://{parsed.netloc}"
        policy = (
            "default-src 'self'; "
            "script-src 'self'; style-src 'self'; "
            "img-src 'self' data: https://tilecache.rainviewer.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org; "
            f"frame-src 'self'{frame_origin}; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", policy)
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    def _json(self, value: Any, status: int = 200, *, head_only: bool = False) -> None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if not head_only:
            self.wfile.write(raw)

    def _error(self, status: int, message: str) -> None:
        self._json({"ok": False, "error": message}, status)

    def _read_json(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            raise RequestError(HTTPStatus.BAD_REQUEST, "Request-Body fehlt")
        try:
            length = int(length_header)
        except ValueError as exc:
            raise RequestError(HTTPStatus.BAD_REQUEST, "Ungültige Content-Length") from exc
        maximum = int(self._config().get("server", {}).get("max_request_bytes", 262144))
        if length > maximum:
            raise RequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request ist zu groß")
        if length <= 0:
            raise RequestError(HTTPStatus.BAD_REQUEST, "Request-Body fehlt")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(HTTPStatus.BAD_REQUEST, "Ungültiges JSON") from exc
        if not isinstance(value, dict):
            raise RequestError(HTTPStatus.BAD_REQUEST, "JSON muss ein Objekt sein")
        return value

    def _token(self) -> str:
        header = self.headers.get("Authorization", "")
        return header[7:].strip() if header.startswith("Bearer ") else ""

    def _authenticated(self) -> bool:
        return self.context.sessions.valid(self._token())

    def _loopback_client(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def _requires_auth(self) -> bool:
        return bool(self._config().get("admin", {}).get("pin_hash"))

    def _guard_admin(self) -> None:
        if not self._authenticated():
            raise RequestError(HTTPStatus.UNAUTHORIZED, "Admin-Anmeldung erforderlich")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch(head_only=True)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch(head_only=False)

    def _dispatch(self, *, head_only: bool) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                self._json({
                    "ok": True,
                    "version": __version__,
                    "uptime_seconds": int(time.monotonic() - self.context.started_at),
                    "state_ready": self.context.state.ready,
                }, head_only=head_only)
                return
            if path == "/api/state":
                self._json(self.context.state.snapshot(), head_only=head_only)
                return
            if path == "/api/admin/status":
                self._json({
                    "ok": True,
                    "pin_configured": self._requires_auth(),
                    "authenticated": self._authenticated(),
                }, head_only=head_only)
                return
            if path == "/api/config":
                if self._requires_auth():
                    self._guard_admin()
                elif not self._loopback_client():
                    raise RequestError(HTTPStatus.FORBIDDEN, "Erstsetup ist nur lokal erlaubt")
                self._json({"path": str(config_path()), "config": public_config(self._config())}, head_only=head_only)
                return
            if path == "/api/station/search":
                self._guard_admin()
                query = parse_qs(parsed.query).get("q", [""])[0]
                self._json({"query": query, "results": search_station(query)}, head_only=head_only)
                return
            if path == "/api/radar":
                self._json(self.context.state.snapshot().get("radar", {}), head_only=head_only)
                return
            self._serve_static(path, head_only=head_only)
        except RequestError as exc:
            self._error(exc.status, str(exc))
        except Exception:
            LOGGER.exception("Unbehandelter GET-Fehler für %s", self.path)
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Interner Serverfehler")

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._read_json()
            path = urlparse(self.path).path
            if path == "/api/admin/setup":
                if self._requires_auth():
                    raise RequestError(HTTPStatus.FORBIDDEN, "Admin-PIN ist bereits eingerichtet")
                if not self._loopback_client():
                    raise RequestError(HTTPStatus.FORBIDDEN, "Erstsetup ist nur lokal erlaubt")
                pin = str(body.get("pin", ""))
                try:
                    encoded = hash_pin(pin)
                except ValueError as exc:
                    raise RequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
                config = self._config()
                config.setdefault("admin", {})["pin_hash"] = encoded
                saved = validate_config(config)
                save_config(saved)
                self.context.replace_config(saved)
                token, expires = self.context.sessions.create()
                self._json({"ok": True, "token": token, "expires_in": expires})
                return
            if path == "/api/admin/login":
                encoded = str(self._config().get("admin", {}).get("pin_hash", ""))
                if not encoded:
                    raise RequestError(HTTPStatus.CONFLICT, "Admin-PIN wurde noch nicht eingerichtet")
                if not verify_pin(str(body.get("pin", "")), encoded):
                    raise RequestError(HTTPStatus.UNAUTHORIZED, "PIN ist falsch")
                token, expires = self.context.sessions.create()
                self._json({"ok": True, "token": token, "expires_in": expires})
                return
            if path == "/api/admin/logout":
                self._guard_admin()
                self.context.sessions.revoke(self._token())
                self._json({"ok": True})
                return
            if path == "/api/config/save":
                self._guard_admin()
                candidate = body.get("config")
                if not isinstance(candidate, dict):
                    raise RequestError(HTTPStatus.BAD_REQUEST, "config fehlt")
                candidate.setdefault("admin", {})["pin_hash"] = self._config().get("admin", {}).get("pin_hash", "")
                try:
                    validated = validate_config(candidate)
                    save_config(validated)
                except ConfigError as exc:
                    raise RequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
                self.context.replace_config(validated)
                self._json({"ok": True, "path": str(config_path()), "config": public_config(validated)})
                return
            raise RequestError(HTTPStatus.NOT_FOUND, "Unbekannter Endpunkt")
        except RequestError as exc:
            self._error(exc.status, str(exc))
        except Exception:
            LOGGER.exception("Unbehandelter POST-Fehler für %s", self.path)
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Interner Serverfehler")

    def _serve_static(self, path: str, *, head_only: bool) -> None:
        if path in {"", "/"}:
            path = "/index.html"
        relative = Path(path.lstrip("/"))
        if ".." in relative.parts:
            raise RequestError(HTTPStatus.FORBIDDEN, "Ungültiger Pfad")
        target = web_directory() / relative
        if not target.is_file():
            raise RequestError(HTTPStatus.NOT_FOUND, "Datei nicht gefunden")
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in {".html", ".css", ".js"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.debug("%s - %s", self.client_address[0], fmt % args)


def create_server(config: dict[str, Any], state: StateManager) -> StorchServer:
    host = str(config["server"]["host"])
    port = int(config["server"]["port"])
    return StorchServer((host, port), ServerContext(config, state))


def run_server(server: StorchServer) -> None:
    server.serve_forever(poll_interval=0.5)
