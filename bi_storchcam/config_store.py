"""Validated, migrated and atomic local configuration storage."""

from __future__ import annotations

import copy
import ipaddress
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .defaults import CONFIG_SCHEMA_VERSION, DEFAULT_CONFIG

LOGGER = logging.getLogger(__name__)

THEMES = {"dark", "light", "high-contrast", "y2k", "dagobert"}
# Tag/Nacht der Bild-Themes (Y2K, Dagobert): automatisch nach Open-Meteo oder fest.
SKY_MODES = {"auto", "day", "night"}
MUSIC_SOURCES = {"off", "auto", "spotify", "ytmusic"}
LAYOUT_PROFILES = {"auto", "minimal", "standard", "information"}
UI_BLOCKS = ("clock", "weather", "transit", "system")
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
BROWSER_KINDS = {"auto", "chromium", "chrome", "edge"}
HARDWARE_PROFILES = {"generic", "raspberry_pi_dsi_portrait", "raspberry_pi_dsi_landscape", "custom"}
ROTATIONS = {"none", "normal", "left", "right", "inverted"}
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
MAX_TRANSIT_STOPS = 20


class ConfigError(ValueError):
    """Raised when a configuration cannot safely be used."""


def platform_app_dir(os_name: str | None = None) -> Path:
    current_os = os.name if os_name is None else os_name
    if current_os == "nt":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / "BI-StorchCam"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "BI-StorchCam"
    return Path.home() / ".config" / "BI-StorchCam"


def default_config_path() -> Path:
    override = os.environ.get("BI_STORCHCAM_CONFIG")
    return Path(os.path.expanduser(override)) if override else platform_app_dir() / "config.json"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{name} muss eine ganze Zahl sein")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} muss eine ganze Zahl sein") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigError(f"{name} muss zwischen {minimum} und {maximum} liegen")
    return parsed


def _bounded_float(value: Any, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"{name} muss eine Zahl sein")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} muss eine Zahl sein") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigError(f"{name} muss zwischen {minimum} und {maximum} liegen")
    return parsed


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} muss true oder false sein")
    return value


def _string(value: Any, name: str, maximum: int = 512) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{name} muss Text sein")
    value = value.strip()
    if len(value) > maximum:
        raise ConfigError(f"{name} ist zu lang")
    return value


def _string_list(value: Any, error: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(error)
    return value


def _only(section: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise ConfigError(f"Unbekannte Felder in {name}: {', '.join(unknown)}")


def _validate_host(host: str) -> str:
    if host in {"localhost", "0.0.0.0", "::", "::1"}:
        return host
    try:
        ipaddress.ip_address(host)
    except ValueError as exc:
        raise ConfigError("server.host muss eine IP-Adresse oder localhost sein") from exc
    return host


def youtube_embed_url(value: str) -> str:
    """Wandelt normale YouTube-Links (watch, youtu.be, live, shorts) in die einbettbare Form um."""
    parsed = urlparse(value)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    video = ""
    if host == "youtu.be":
        video = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "music.youtube.com"}:
        parts = parsed.path.strip("/").split("/")
        if parts[0] == "watch":
            video = parse_qs(parsed.query).get("v", [""])[0]
        elif parts[0] in {"live", "shorts"} and len(parts) > 1:
            video = parts[1]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        return f"https://www.youtube.com/embed/{video}"
    return value


def _validate_stream_url(value: str) -> str:
    if not value:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("stream.url muss eine vollständige HTTP- oder HTTPS-URL sein")
    return youtube_embed_url(value)


def _validate_browser(browser: str) -> str:
    if browser.lower() in BROWSER_KINDS:
        return browser
    browser_path = Path(os.path.expanduser(browser))
    if not browser_path.is_absolute():
        raise ConfigError("kiosk.browser muss auto, chromium, chrome, edge oder ein absoluter Pfad sein")
    browser_name = browser_path.name.lower()
    if not any(name in browser_name for name in ("chromium", "chrome", "msedge", "edge")):
        raise ConfigError("Der absolute Browserpfad muss Chromium, Chrome oder Edge referenzieren")
    return browser


def _validate_stop(raw: Any, index: int, default_max: int) -> dict[str, Any]:
    name = f"transit.stops[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{name} muss ein Objekt sein")
    allowed = {
        "title", "station_name", "station_id", "line_filter", "nightbus_only", "hide_if_empty", "max_rows"
    }
    _only(raw, allowed, name)
    filters = _string_list(raw.get("line_filter", []), f"{name}.line_filter muss eine Textliste sein")
    station_id = _string(raw.get("station_id", ""), f"{name}.station_id", 80)
    station_name = _string(raw.get("station_name", ""), f"{name}.station_name", 160)
    if not station_id and not station_name:
        raise ConfigError(f"{name} benötigt Haltestellen-ID oder -Name")
    return {
        "title": _string(raw.get("title", station_name), f"{name}.title", 80),
        "station_name": station_name,
        "station_id": station_id,
        "line_filter": [_string(item, "Linienfilter", 20) for item in filters if item.strip()],
        "nightbus_only": _bool(raw.get("nightbus_only", False), "nightbus_only"),
        "hide_if_empty": _bool(raw.get("hide_if_empty", True), "hide_if_empty"),
        "max_rows": _bounded_int(raw.get("max_rows", default_max), "max_rows", 1, 12),
    }


def migrate_config(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Migrate known historic values and discard obsolete application branches."""
    source = copy.deepcopy(raw)
    migrated: dict[str, Any] = {}
    for section in DEFAULT_CONFIG:
        if section in source and isinstance(source[section], dict):
            migrated[section] = source[section]

    app = migrated.setdefault("app", {})
    previous = int(app.get("config_schema_version", 0) or 0)
    app["config_schema_version"] = CONFIG_SCHEMA_VERSION

    screen = migrated.setdefault("screen", {})
    if previous < CONFIG_SCHEMA_VERSION:
        old_profile = str(screen.pop("profile", "") or "")
        if "portrait" in old_profile:
            screen["hardware_profile"] = "raspberry_pi_dsi_portrait"
        screen.setdefault("hardware_profile", "generic")
        if screen.get("output") == "DSI-2" and screen.get("rotation") == "right":
            screen.update({"output": "auto", "rotation": "none", "touch_matrix": ""})
        screen.pop("width", None)
        screen.pop("height", None)

    kiosk = migrated.setdefault("kiosk", {})
    kiosk.pop("display", None)
    kiosk.pop("xauthority", None)
    kiosk.pop("kill_existing_chromium", None)

    ui = migrated.setdefault("ui", {})
    ui.pop("menu_enabled", None)
    ui.pop("radar", None)  # Radar wurde entfernt; der Abschnitt „radar“ fällt oben automatisch weg.
    for name in UI_BLOCKS:
        section = ui.get(name)
        if isinstance(section, dict):
            for obsolete in ("position", "size", "mode", "diagnostic_only", "refresh_seconds"):
                section.pop(obsolete, None)
    if ui.get("layout_profile") not in LAYOUT_PROFILES:
        ui["layout_profile"] = "auto"
    if ui.get("theme") not in THEMES:
        ui["theme"] = "dark"
    if ui.get("sky", "auto") not in SKY_MODES:
        ui["sky"] = "auto"
    music = migrated.get("music")
    if isinstance(music, dict):
        music.pop("ytmusic", None)  # Google-Client der gesperrten Geräteanmeldung; YouTube Music meldet sich jetzt im Browser an.
        music.pop("lastfm", None)  # Last.fm wurde entfernt.
        if music.get("source") == "lastfm":
            music["source"] = "auto"

    transit = migrated.setdefault("transit", {})
    stops = transit.get("stops")
    if isinstance(stops, list):
        transit["stops"] = [
            stop for stop in stops
            if isinstance(stop, dict) and str(stop.get("title", "")).upper() != "BEISPIEL"
        ]

    return migrated, migrated != raw


def _validate_app(app: dict[str, Any]) -> None:
    _only(app, {"name", "language", "timezone", "cache_dir", "config_schema_version"}, "app")
    timezone = _string(app["timezone"], "app.timezone", 80)
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"Unbekannte Zeitzone: {timezone}") from exc
    app.update({
        "name": "BI-StorchCam",
        "language": _string(app["language"], "app.language", 10) or "de",
        "timezone": timezone,
        "cache_dir": _string(app["cache_dir"], "app.cache_dir", 512),
        "config_schema_version": CONFIG_SCHEMA_VERSION,
    })


def _validate_server(server: dict[str, Any]) -> None:
    _only(server, {"host", "port", "max_request_bytes", "admin_session_minutes"}, "server")
    server.update({
        "host": _validate_host(_string(server["host"], "server.host", 80)),
        "port": _bounded_int(server["port"], "server.port", 1024, 65535),
        "max_request_bytes": _bounded_int(server["max_request_bytes"], "server.max_request_bytes", 4096, 1048576),
        "admin_session_minutes": _bounded_int(server["admin_session_minutes"], "server.admin_session_minutes", 5, 240),
    })


def _validate_kiosk(kiosk: dict[str, Any]) -> None:
    _only(kiosk, {
        "enabled", "browser", "profile_dir", "disable_screensaver", "use_gpu", "browser_restart_seconds",
        "browser_restart_max_seconds", "browser_stable_seconds", "browser_max_failures", "log_file",
        "log_max_bytes", "log_backups", "extra_flags",
    }, "kiosk")
    browser = _validate_browser(_string(kiosk["browser"], "kiosk.browser", 512))
    extra_flags = _string_list(kiosk["extra_flags"], "kiosk.extra_flags muss eine Textliste sein")
    kiosk.update({
        "enabled": _bool(kiosk["enabled"], "kiosk.enabled"),
        "browser": browser,
        "profile_dir": _string(kiosk["profile_dir"], "kiosk.profile_dir", 512),
        "disable_screensaver": _bool(kiosk["disable_screensaver"], "kiosk.disable_screensaver"),
        "use_gpu": _bool(kiosk["use_gpu"], "kiosk.use_gpu"),
        "browser_restart_seconds": _bounded_int(kiosk["browser_restart_seconds"], "browser_restart_seconds", 1, 60),
        "browser_restart_max_seconds": _bounded_int(kiosk["browser_restart_max_seconds"], "browser_restart_max_seconds", 5, 600),
        "browser_stable_seconds": _bounded_int(kiosk["browser_stable_seconds"], "browser_stable_seconds", 10, 3600),
        "browser_max_failures": _bounded_int(kiosk["browser_max_failures"], "browser_max_failures", 1, 50),
        "log_file": _string(kiosk["log_file"], "kiosk.log_file", 512),
        "log_max_bytes": _bounded_int(kiosk["log_max_bytes"], "kiosk.log_max_bytes", 65536, 104857600),
        "log_backups": _bounded_int(kiosk["log_backups"], "kiosk.log_backups", 1, 20),
        "extra_flags": [_string(item, "Browserflag", 200) for item in extra_flags],
    })


def _validate_screen(screen: dict[str, Any]) -> None:
    _only(screen, {"hardware_profile", "output", "rotation", "touch_device", "touch_matrix"}, "screen")
    profile = _string(screen["hardware_profile"], "screen.hardware_profile", 80)
    if profile not in HARDWARE_PROFILES:
        raise ConfigError("Ungültiges screen.hardware_profile")
    rotation = _string(screen["rotation"], "screen.rotation", 20)
    if rotation not in ROTATIONS:
        raise ConfigError("Ungültige screen.rotation")
    screen.update({
        "hardware_profile": profile,
        "output": _string(screen["output"], "screen.output", 80) or "auto",
        "rotation": rotation,
        "touch_device": _string(screen["touch_device"], "screen.touch_device", 160),
        "touch_matrix": _string(screen["touch_matrix"], "screen.touch_matrix", 200),
    })


def _validate_location(location: dict[str, Any]) -> None:
    _only(location, {"label", "latitude", "longitude"}, "location")
    location.update({
        "label": _string(location["label"], "location.label", 120) or "Bielefeld",
        "latitude": _bounded_float(location["latitude"], "location.latitude", -90, 90),
        "longitude": _bounded_float(location["longitude"], "location.longitude", -180, 180),
    })


def _validate_stream(stream: dict[str, Any]) -> None:
    _only(stream, {"url", "muted", "autoplay"}, "stream")
    stream.update({
        "url": _validate_stream_url(_string(stream["url"], "stream.url", 2048)),
        "muted": _bool(stream["muted"], "stream.muted"),
        "autoplay": _bool(stream["autoplay"], "stream.autoplay"),
    })


def _validate_admin(admin: dict[str, Any], server_host: str) -> None:
    _only(admin, {"pin_hash", "require_pin"}, "admin")
    admin["pin_hash"] = _string(admin["pin_hash"], "admin.pin_hash", 512)
    admin["require_pin"] = _bool(admin["require_pin"], "admin.require_pin")
    if server_host not in LOOPBACK_HOSTS and admin["require_pin"] and not admin["pin_hash"]:
        raise ConfigError("Eine externe Bind-Adresse erfordert zuerst eine konfigurierte Admin-PIN")


def _validate_youtube(youtube: dict[str, Any]) -> None:
    _only(youtube, {"api_key", "default_query"}, "youtube")
    api_key = _string(youtube["api_key"], "youtube.api_key", 200)
    if api_key and not re.fullmatch(r"[A-Za-z0-9_-]+", api_key):
        raise ConfigError("youtube.api_key enthält ungültige Zeichen")
    youtube.update({
        "api_key": api_key,
        "default_query": _string(youtube["default_query"], "youtube.default_query", 100),
    })


def _validate_music(music: dict[str, Any]) -> None:
    _only(music, {"source", "spotify"}, "music")
    source = _string(music["source"], "music.source", 10)
    if source not in MUSIC_SOURCES:
        raise ConfigError("Ungültige music.source")
    _only(music["spotify"], {"client_id"}, "music.spotify")
    client_id = _string(music["spotify"]["client_id"], "music.spotify.client_id", 64).strip()
    if client_id and not re.fullmatch(r"[A-Za-z0-9]+", client_id):
        raise ConfigError("Die Spotify-Client-ID enthält ungültige Zeichen")
    music.update({
        "source": source,
        "spotify": {"client_id": client_id},
    })


def _validate_ui(ui: dict[str, Any]) -> None:
    _only(ui, {"theme", "sky", "layout_profile", *UI_BLOCKS}, "ui")
    theme = _string(ui["theme"], "ui.theme", 30)
    sky = _string(ui["sky"], "ui.sky", 10)
    if sky not in SKY_MODES:
        raise ConfigError("Ungültiges ui.sky")
    ui["sky"] = sky
    layout = _string(ui["layout_profile"], "ui.layout_profile", 30)
    if theme not in THEMES:
        raise ConfigError("Ungültiges ui.theme")
    if layout not in LAYOUT_PROFILES:
        raise ConfigError("Ungültiges ui.layout_profile")
    ui["theme"] = theme
    ui["layout_profile"] = layout
    for name in UI_BLOCKS:
        _only(ui[name], {"enabled"}, f"ui.{name}")
        ui[name]["enabled"] = _bool(ui[name]["enabled"], f"ui.{name}.enabled")


def _validate_weather(weather: dict[str, Any]) -> None:
    _only(weather, {"provider", "refresh_seconds", "forecast_hours", "rain_mm_threshold", "rain_probability_threshold"}, "weather")
    if _string(weather["provider"], "weather.provider", 40) != "openmeteo":
        raise ConfigError("Derzeit wird nur der Wetterprovider openmeteo unterstützt")
    weather.update({
        "provider": "openmeteo",
        "refresh_seconds": _bounded_int(weather["refresh_seconds"], "weather.refresh_seconds", 60, 3600),
        "forecast_hours": _bounded_int(weather["forecast_hours"], "weather.forecast_hours", 1, 48),
        "rain_mm_threshold": _bounded_float(weather["rain_mm_threshold"], "rain_mm_threshold", 0, 100),
        "rain_probability_threshold": _bounded_int(weather["rain_probability_threshold"], "rain_probability_threshold", 0, 100),
    })


def _validate_transit(transit: dict[str, Any]) -> None:
    _only(transit, {"provider", "refresh_seconds", "default_max_rows", "target_len", "stops"}, "transit")
    if _string(transit["provider"], "transit.provider", 40) != "vrr":
        raise ConfigError("Derzeit wird nur der ÖPNV-Provider vrr unterstützt")
    default_max = _bounded_int(transit["default_max_rows"], "transit.default_max_rows", 1, 12)
    stops = transit["stops"]
    if not isinstance(stops, list) or len(stops) > MAX_TRANSIT_STOPS:
        raise ConfigError(f"transit.stops muss eine Liste mit höchstens {MAX_TRANSIT_STOPS} Einträgen sein")
    transit.update({
        "provider": "vrr",
        "refresh_seconds": _bounded_int(transit["refresh_seconds"], "transit.refresh_seconds", 15, 3600),
        "default_max_rows": default_max,
        "target_len": _bounded_int(transit["target_len"], "transit.target_len", 8, 80),
        "stops": [_validate_stop(stop, index, default_max) for index, stop in enumerate(stops)],
    })


def _validate_logging(logging_cfg: dict[str, Any]) -> None:
    _only(logging_cfg, {"level", "max_bytes", "backups"}, "logging")
    level = _string(logging_cfg["level"], "logging.level", 20).upper()
    if level not in LOG_LEVELS:
        raise ConfigError("Ungültiges logging.level")
    logging_cfg.update({
        "level": level,
        "max_bytes": _bounded_int(logging_cfg["max_bytes"], "logging.max_bytes", 65536, 104857600),
        "backups": _bounded_int(logging_cfg["backups"], "logging.backups", 1, 20),
    })


def validate_config(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError("Die Konfiguration muss ein JSON-Objekt sein")
    _only(raw, set(DEFAULT_CONFIG), "Konfiguration")
    cfg = deep_merge(DEFAULT_CONFIG, raw)
    _validate_app(cfg["app"])
    _validate_server(cfg["server"])
    _validate_kiosk(cfg["kiosk"])
    _validate_screen(cfg["screen"])
    _validate_location(cfg["location"])
    _validate_stream(cfg["stream"])
    _validate_admin(cfg["admin"], cfg["server"]["host"])
    _validate_youtube(cfg["youtube"])
    _validate_music(cfg["music"])
    _validate_ui(cfg["ui"])
    _validate_weather(cfg["weather"])
    _validate_transit(cfg["transit"])
    _validate_logging(cfg["logging"])
    return cfg


def _read_migrated(path: Path) -> tuple[dict[str, Any], bool]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return migrate_config(raw)


def _migrate_legacy_windows_config(target: Path) -> None:
    legacy = Path.home() / ".config" / "BI-StorchCam" / "config.json"
    if not legacy.exists() or legacy == target:
        return
    try:
        migrated, _ = _read_migrated(legacy)
        save_config(validate_config(migrated), target)
        LOGGER.info("Windows-Konfiguration einmalig von %s nach %s migriert", legacy, target)
    except (OSError, json.JSONDecodeError, ConfigError) as exc:
        LOGGER.error("Legacy-Windows-Konfiguration konnte nicht migriert werden: %s", exc)


def _backup_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".bak")


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or default_config_path()
    if path is None and os.name == "nt" and not target.exists():
        _migrate_legacy_windows_config(target)
    if not target.exists():
        return validate_config(copy.deepcopy(DEFAULT_CONFIG))
    try:
        migrated, changed = _read_migrated(target)
        validated = validate_config(migrated)
        if changed:
            save_config(validated, target)
        return validated
    except (OSError, json.JSONDecodeError, ConfigError) as primary_error:
        backup = _backup_path(target)
        LOGGER.error("Konfiguration %s ist ungültig: %s", target, primary_error)
        if backup.exists():
            try:
                migrated, _ = _read_migrated(backup)
                validated = validate_config(migrated)
                LOGGER.warning("Verwende letzte gültige Sicherung %s", backup)
                return validated
            except (OSError, json.JSONDecodeError, ConfigError) as backup_error:
                raise ConfigError(f"Konfiguration und Sicherung sind ungültig: {primary_error}; {backup_error}") from backup_error
        raise ConfigError(f"Konfiguration ist ungültig: {primary_error}") from primary_error


def _fsync_directory(directory: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    directory_fd = os.open(directory, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def save_config(config: dict[str, Any], path: Path | None = None) -> Path:
    target = path or default_config_path()
    validated = validate_config(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, _backup_path(target))
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(validated, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def config_path() -> Path:
    target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def cache_dir(config: dict[str, Any]) -> Path:
    raw = str(config.get("app", {}).get("cache_dir", "~/.cache/BI-StorchCam"))
    target = Path(os.path.expandvars(os.path.expanduser(raw)))
    target.mkdir(parents=True, exist_ok=True)
    return target


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    safe = copy.deepcopy(config)
    safe.setdefault("admin", {})["pin_hash"] = ""
    safe.setdefault("youtube", {})["api_key"] = ""
    return safe


def youtube_api_key(config: dict[str, Any]) -> str:
    """Schlüssel aus dem Menü hat Vorrang, sonst die Umgebungsvariable YOUTUBE_API_KEY."""
    return str(config.get("youtube", {}).get("api_key", "")) or os.environ.get("YOUTUBE_API_KEY", "").strip()
