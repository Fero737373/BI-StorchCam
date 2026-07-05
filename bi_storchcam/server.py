# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config_store import CONFIG_PATH, load_config, save_config
from .providers.rainviewer import get_radar_metadata
from .providers.transit_vrr_smart import search_station
from .state import build_state

WEB_DIR = Path(__file__).resolve().parent / "web"


class StorchHandler(BaseHTTPRequestHandler):
    server_version = "BI-StorchCam/2.1"

    def _json(self, obj: Any, status: int = 200) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    @property
    def config(self) -> dict[str, Any]:
        return load_config()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/state":
            self._json(build_state(self.config))
            return
        if path == "/api/config":
            self._json({"path": str(CONFIG_PATH), "config": self.config})
            return
        if path == "/api/station/search":
            q = parse_qs(parsed.query).get("q", [""])[0]
            self._json({"query": q, "results": search_station(q)})
            return
        if path in ("/api/radar", "/api/radar/test"):
            self._json(get_radar_metadata(self.config))
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/config/save":
            body = self._read_json_body()
            cfg = body.get("config") if isinstance(body, dict) else None
            if not isinstance(cfg, dict):
                self._json({"ok": False, "error": "config fehlt"}, 400)
                return
            save_config(cfg)
            self._json({"ok": True, "path": str(CONFIG_PATH)})
            return
        self._json({"ok": False, "error": "unknown endpoint"}, 404)

    def _serve_static(self, path: str) -> None:
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        if ".." in Path(rel).parts:
            self.send_error(403)
            return
        file_path = WEB_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        data = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif file_path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def run_server(host: str, port: int) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), StorchHandler)
    httpd.serve_forever()
    return httpd
