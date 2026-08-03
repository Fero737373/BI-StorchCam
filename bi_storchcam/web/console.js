"use strict";

(() => {
  const consoleButton = document.getElementById("consoleToggle");
  const bluetoothButton = document.getElementById("bluetoothConnect");
  const bluetoothStatus = document.getElementById("bluetoothStatus");
  const bluetoothDialog = document.getElementById("bluetoothDialog");
  const closeBluetoothButton = document.getElementById("closeBluetooth");
  const scanBluetoothButton = document.getElementById("bluetoothScan");
  const bluetoothDialogStatus = document.getElementById("bluetoothDialogStatus");
  const bluetoothDevices = document.getElementById("bluetoothDevices");

  if (!consoleButton || !bluetoothButton || !bluetoothStatus) return;

  let consoleBusy = false;
  let consoleState = "unavailable";
  let bluetoothBusy = false;

  function adminToken() {
    return sessionStorage.getItem("bi-storchcam-admin-token") || "";
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = adminToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, headers, cache: "no-store" });
    const payload = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function renderConsole(payload) {
    const state = payload?.state || "unavailable";
    consoleState = state;
    consoleButton.dataset.state = state;
    consoleButton.classList.toggle("button-danger", state === "running");
    consoleButton.classList.toggle("button-secondary", state !== "running");

    if (state === "running") {
      consoleButton.textContent = "Konsole beenden";
      consoleButton.title = "KonsolenDocker auf dem HDMI-Bildschirm beenden";
    } else if (state === "stopped") {
      consoleButton.textContent = "Konsole starten";
      consoleButton.title = "KonsolenDocker auf dem HDMI-Bildschirm starten";
    } else {
      consoleButton.textContent = "Konsole nicht bereit";
      consoleButton.title = payload?.message || "KonsolenDocker ist auf diesem Gerät nicht verfügbar";
    }
    updateConsoleDisabled();
  }

  function updateConsoleDisabled() {
    consoleButton.disabled = consoleBusy || consoleState === "unavailable";
  }

  function showBluetoothStatus(message, state = "") {
    bluetoothStatus.textContent = message;
    bluetoothStatus.dataset.state = state;
  }

  function setDialogStatus(message, state = "") {
    if (!bluetoothDialogStatus) return;
    bluetoothDialogStatus.textContent = message;
    bluetoothDialogStatus.className = "status-message";
    if (state) bluetoothDialogStatus.classList.add(state);
  }

  async function refreshConsole() {
    if (consoleBusy) return;
    try {
      renderConsole(await request("/api/console/status"));
    } catch (error) {
      renderConsole({ state: "unavailable", message: error.message });
    }
  }

  async function toggleConsole() {
    if (consoleBusy) return;
    consoleBusy = true;
    updateConsoleDisabled();
    consoleButton.textContent = "Konsole wird umgeschaltet …";
    try {
      renderConsole(await request("/api/console/toggle", {
        method: "POST",
        body: "{}",
      }));
      window.setTimeout(refreshConsole, 1500);
    } catch (error) {
      renderConsole({ state: "unavailable", message: error.message });
    } finally {
      consoleBusy = false;
      updateConsoleDisabled();
    }
  }

  function deviceSymbol(kind) {
    return {
      controller: "🎮",
      audio: "♫",
      keyboard: "⌨",
      mouse: "●",
      phone: "▯",
      tv: "▣",
      device: "◆",
    }[kind] || "◆";
  }

  function badge(text, className = "") {
    const element = document.createElement("span");
    element.className = `bluetooth-badge${className ? ` ${className}` : ""}`;
    element.textContent = text;
    return element;
  }

  function emptyDeviceList(message) {
    if (!bluetoothDevices) return;
    const empty = document.createElement("div");
    empty.className = "bluetooth-empty";
    empty.textContent = message;
    bluetoothDevices.replaceChildren(empty);
  }

  function renderDevices(devices) {
    if (!bluetoothDevices) return;
    bluetoothDevices.replaceChildren();
    if (!Array.isArray(devices) || devices.length === 0) {
      emptyDeviceList("Keine Bluetooth-Geräte gefunden. Aktiviere den Pairing-Modus und starte die Suche erneut.");
      return;
    }

    devices.forEach((device) => {
      const row = document.createElement("article");
      row.className = "bluetooth-device";
      row.dataset.connected = String(Boolean(device.connected));

      const icon = document.createElement("span");
      icon.className = "bluetooth-device-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = deviceSymbol(device.kind);

      const copy = document.createElement("div");
      copy.className = "bluetooth-device-copy";
      const name = document.createElement("strong");
      name.className = "bluetooth-device-name";
      name.textContent = device.name || "Unbekanntes Gerät";
      const address = document.createElement("span");
      address.className = "bluetooth-device-address";
      address.textContent = device.address || "";
      const meta = document.createElement("div");
      meta.className = "bluetooth-device-meta";
      if (device.connected) meta.appendChild(badge("Verbunden", "connected"));
      if (device.paired) meta.appendChild(badge("Gekoppelt"));
      if (device.trusted) meta.appendChild(badge("Vertrauenswürdig"));
      if (Number.isInteger(device.rssi)) meta.appendChild(badge(`Signal ${device.rssi} dBm`));
      copy.append(name, address, meta);

      const actions = document.createElement("div");
      actions.className = "bluetooth-device-actions";
      const connectButton = document.createElement("button");
      connectButton.type = "button";
      connectButton.className = device.connected ? "button button-danger" : "button button-primary";
      connectButton.textContent = device.connected ? "Trennen" : "Verbinden";
      connectButton.disabled = bluetoothBusy || device.blocked;
      connectButton.addEventListener("click", () => changeConnection(device));
      actions.appendChild(connectButton);

      if (device.paired && !device.connected) {
        const forgetButton = document.createElement("button");
        forgetButton.type = "button";
        forgetButton.className = "button button-secondary bluetooth-forget";
        forgetButton.title = `${device.name || "Gerät"} vergessen`;
        forgetButton.setAttribute("aria-label", forgetButton.title);
        forgetButton.textContent = "×";
        forgetButton.disabled = bluetoothBusy;
        forgetButton.addEventListener("click", () => forgetDevice(device));
        actions.appendChild(forgetButton);
      }

      row.append(icon, copy, actions);
      bluetoothDevices.appendChild(row);
    });
  }

  function setBluetoothBusy(busy, label = "") {
    bluetoothBusy = busy;
    bluetoothButton.disabled = busy;
    if (scanBluetoothButton) {
      scanBluetoothButton.disabled = busy;
      scanBluetoothButton.innerHTML = busy
        ? `<span class="bluetooth-spinner" aria-hidden="true"></span>${label || "Bitte warten"}`
        : "Nach Geräten suchen";
    }
  }

  async function loadDevices({ quiet = false } = {}) {
    if (!quiet) setDialogStatus("Bekannte Geräte werden geladen.");
    try {
      const payload = await request("/api/bluetooth/devices");
      renderDevices(payload.devices || []);
      if (!quiet) setDialogStatus(`${(payload.devices || []).length} Gerät(e) bekannt.`, "success");
      return payload.devices || [];
    } catch (error) {
      emptyDeviceList(error.message);
      setDialogStatus(error.message, "error");
      showBluetoothStatus(error.message, "error");
      return [];
    }
  }

  async function scanDevices() {
    if (bluetoothBusy) return;
    setBluetoothBusy(true, "Suche läuft …");
    setDialogStatus("Bluetooth-Geräte werden gesucht. Neue Geräte müssen jetzt im Pairing-Modus sein.");
    try {
      const payload = await request("/api/bluetooth/scan", {
        method: "POST",
        body: JSON.stringify({ seconds: 12 }),
      });
      const devices = payload.devices || [];
      renderDevices(devices);
      setDialogStatus(`${devices.length} Gerät(e) gefunden.`, "success");
      showBluetoothStatus(devices.some((device) => device.connected) ? "Bluetooth-Gerät verbunden" : "", "success");
    } catch (error) {
      setDialogStatus(error.message, "error");
      showBluetoothStatus(error.message, "error");
    } finally {
      setBluetoothBusy(false);
    }
  }

  async function changeConnection(device) {
    if (bluetoothBusy || !device?.address) return;
    const action = device.connected ? "disconnect" : "connect";
    setBluetoothBusy(true, device.connected ? "Wird getrennt …" : "Wird verbunden …");
    setDialogStatus(`${device.name || "Gerät"} ${device.connected ? "wird getrennt" : "wird verbunden"} …`);
    try {
      const payload = await request(`/api/bluetooth/${action}`, {
        method: "POST",
        body: JSON.stringify({ address: device.address }),
      });
      const result = payload.device || device;
      const message = result.connected
        ? `${result.name || "Gerät"} ist verbunden.`
        : `${result.name || "Gerät"} wurde getrennt.`;
      setDialogStatus(message, "success");
      showBluetoothStatus(message, "success");
      await loadDevices({ quiet: true });
    } catch (error) {
      setDialogStatus(error.message, "error");
      showBluetoothStatus(error.message, "error");
    } finally {
      setBluetoothBusy(false);
    }
  }

  async function forgetDevice(device) {
    if (bluetoothBusy || !device?.address) return;
    if (!window.confirm(`${device.name || "Dieses Gerät"} wirklich aus der Bluetooth-Liste entfernen?`)) return;
    setBluetoothBusy(true, "Gerät wird entfernt …");
    try {
      await request("/api/bluetooth/remove", {
        method: "POST",
        body: JSON.stringify({ address: device.address }),
      });
      setDialogStatus(`${device.name || "Gerät"} wurde entfernt.`, "success");
      showBluetoothStatus("");
      await loadDevices({ quiet: true });
    } catch (error) {
      setDialogStatus(error.message, "error");
      showBluetoothStatus(error.message, "error");
    } finally {
      setBluetoothBusy(false);
    }
  }

  async function openBluetoothDialog() {
    if (!bluetoothDialog || !bluetoothDevices || !scanBluetoothButton) {
      showBluetoothStatus("Bluetooth-Geräteübersicht ist nicht verfügbar.", "error");
      return;
    }
    if (!bluetoothDialog.open) bluetoothDialog.showModal();
    const devices = await loadDevices();
    if (!devices.some((device) => device.connected)) scanDevices();
  }

  function closeBluetoothDialog() {
    if (bluetoothDialog?.open && !bluetoothBusy) bluetoothDialog.close();
    bluetoothButton.focus();
  }

  consoleButton.addEventListener("click", toggleConsole);
  bluetoothButton.addEventListener("click", openBluetoothDialog);
  closeBluetoothButton?.addEventListener("click", closeBluetoothDialog);
  scanBluetoothButton?.addEventListener("click", scanDevices);
  bluetoothDialog?.addEventListener("cancel", (event) => {
    if (bluetoothBusy) event.preventDefault();
  });
  bluetoothDialog?.addEventListener("click", (event) => {
    if (event.target === bluetoothDialog && !bluetoothBusy) closeBluetoothDialog();
  });

  refreshConsole();
  window.setInterval(refreshConsole, 10000);
})();
