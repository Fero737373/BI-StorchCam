"""Local BlueZ bridge for the BI-StorchCam Bluetooth device picker."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Final

BLUETOOTHCTL: Final = "bluetoothctl"
ADDRESS_PATTERN: Final = re.compile(r"^[0-9A-F]{2}(?::[0-9A-F]{2}){5}$")
DEVICE_PATTERN: Final = re.compile(r"^Device\s+([0-9A-Fa-f:]{17})\s+(.+)$")


class BluetoothControlError(RuntimeError):
    """Raised when BlueZ cannot complete a requested operation."""


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    return environment


def _run(arguments: list[str], *, timeout: int = 12) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(BLUETOOTHCTL)
    if not executable:
        raise BluetoothControlError("Bluetooth-Unterstützung fehlt. Installiere das Paket bluez.")
    try:
        return subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_environment(),
        )
    except subprocess.TimeoutExpired as exc:
        raise BluetoothControlError("Bluetooth reagiert nicht rechtzeitig.") from exc
    except OSError as exc:
        raise BluetoothControlError(f"Bluetooth konnte nicht ausgeführt werden: {exc}") from exc


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())


def _require_success(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    output = _output(result)
    lowered = output.lower()
    if result.returncode != 0 or "failed to" in lowered or "not available" in lowered:
        detail = next((line.strip() for line in reversed(output.splitlines()) if line.strip()), fallback)
        raise BluetoothControlError(detail)
    return output


def _normalise_address(address: str) -> str:
    normalised = address.strip().upper()
    if not ADDRESS_PATTERN.fullmatch(normalised):
        raise BluetoothControlError("Ungültige Bluetooth-Adresse.")
    return normalised


def _properties(output: str) -> dict[str, str]:
    properties: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in {"Name", "Alias", "Icon", "Paired", "Trusted", "Connected", "Blocked", "RSSI"}:
            properties[key] = value.strip()
    return properties


def _yes(properties: dict[str, str], key: str) -> bool:
    return properties.get(key, "").lower() == "yes"


def _device_kind(name: str, icon: str) -> str:
    value = f"{name} {icon}".lower()
    if any(token in value for token in ("controller", "gamepad", "dualshock", "dualsense", "xbox", "8bitdo", "joy-con", "input-gaming")):
        return "controller"
    if any(token in value for token in ("headset", "headphone", "speaker", "audio")):
        return "audio"
    if "keyboard" in value:
        return "keyboard"
    if "mouse" in value:
        return "mouse"
    if any(token in value for token in ("phone", "android", "iphone")):
        return "phone"
    if any(token in value for token in ("television", "android tv", " tv")):
        return "tv"
    return "device"


def _ensure_adapter() -> None:
    adapters = _require_success(_run(["list"]), "Kein Bluetooth-Adapter wurde gefunden.")
    if not adapters.strip():
        raise BluetoothControlError("Kein Bluetooth-Adapter wurde gefunden.")
    _require_success(_run(["power", "on"]), "Bluetooth konnte nicht eingeschaltet werden.")


def _device_info(address: str, fallback_name: str = "") -> dict[str, Any]:
    result = _run(["info", address])
    output = _output(result)
    properties = _properties(output)
    name = properties.get("Alias") or properties.get("Name") or fallback_name or address
    icon = properties.get("Icon", "")
    rssi_text = properties.get("RSSI", "")
    try:
        rssi: int | None = int(rssi_text)
    except ValueError:
        rssi = None
    return {
        "address": address,
        "name": name,
        "kind": _device_kind(name, icon),
        "icon": icon,
        "paired": _yes(properties, "Paired"),
        "trusted": _yes(properties, "Trusted"),
        "connected": _yes(properties, "Connected"),
        "blocked": _yes(properties, "Blocked"),
        "rssi": rssi,
    }


def list_devices() -> list[dict[str, Any]]:
    """Return all devices currently known to BlueZ."""
    _ensure_adapter()
    result = _run(["devices"])
    devices: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        match = DEVICE_PATTERN.match(line.strip())
        if not match:
            continue
        address = match.group(1).upper()
        if address in seen:
            continue
        seen.add(address)
        devices.append(_device_info(address, match.group(2).strip()))
    devices.sort(
        key=lambda device: (
            not bool(device["connected"]),
            not bool(device["paired"]),
            str(device["name"]).lower(),
            str(device["address"]),
        )
    )
    return devices


def scan_devices(seconds: int = 12) -> list[dict[str, Any]]:
    """Scan briefly and then return all discovered devices."""
    if seconds < 3 or seconds > 30:
        raise BluetoothControlError("Die Suchdauer muss zwischen 3 und 30 Sekunden liegen.")
    _ensure_adapter()
    _run(["pairable", "on"])
    try:
        _run(["--timeout", str(seconds), "scan", "on"], timeout=seconds + 5)
    finally:
        _run(["scan", "off"])
    return list_devices()


def connect_device(address: str) -> dict[str, Any]:
    """Pair when needed, trust and connect one selected device."""
    address = _normalise_address(address)
    _ensure_adapter()
    _run(["pairable", "on"])
    device = _device_info(address)
    if not device["paired"]:
        pair_result = _run(
            ["--agent", "NoInputNoOutput", "--timeout", "35", "pair", address],
            timeout=40,
        )
        _require_success(pair_result, "Kopplung ist fehlgeschlagen.")
    _require_success(_run(["trust", address]), "Gerät konnte nicht als vertrauenswürdig gespeichert werden.")
    _require_success(_run(["connect", address], timeout=20), "Verbindung ist fehlgeschlagen.")
    device = _device_info(address)
    if not device["connected"]:
        raise BluetoothControlError(f"{device['name']} wurde gekoppelt, ist aber noch nicht verbunden.")
    return device


def disconnect_device(address: str) -> dict[str, Any]:
    """Disconnect one selected device without forgetting it."""
    address = _normalise_address(address)
    _ensure_adapter()
    _require_success(_run(["disconnect", address]), "Gerät konnte nicht getrennt werden.")
    return _device_info(address)


def remove_device(address: str) -> dict[str, Any]:
    """Forget a paired device."""
    address = _normalise_address(address)
    _ensure_adapter()
    device = _device_info(address)
    _require_success(_run(["remove", address]), "Gerät konnte nicht entfernt werden.")
    return {"address": address, "name": device["name"], "removed": True}
