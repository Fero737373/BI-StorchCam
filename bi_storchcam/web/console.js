"use strict";

(() => {
  const consoleButton = document.getElementById("consoleToggle");
  const bluetoothButton = document.getElementById("bluetoothConnect");
  const bluetoothStatus = document.getElementById("bluetoothStatus");
  if (!consoleButton || !bluetoothButton || !bluetoothStatus) return;

  let consoleBusy = false;
  let bluetoothBusy = false;
  let consoleState = "unavailable";
  let bluetoothResetTimer = 0;

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

  function render(payload) {
    const state = payload?.state || "unavailable";
    consoleState = state;
    consoleButton.dataset.state = state;
    consoleButton.classList.toggle("button-danger", state === "running");
    consoleButton.classList.toggle("button-secondary", state !== "running");

    if (state === "running") {
      consoleButton.textContent = "Konsole beenden";
      consoleButton.title = "KonsolenDocker auf dem HDMI-Bildschirm beenden";
      updateDisabled();
      return;
    }
    if (state === "stopped") {
      consoleButton.textContent = "Konsole starten";
      consoleButton.title = "KonsolenDocker auf dem HDMI-Bildschirm starten";
      updateDisabled();
      return;
    }

    consoleButton.textContent = "Konsole nicht bereit";
    consoleButton.title = payload?.message || "KonsolenDocker ist auf diesem Gerät nicht verfügbar";
    updateDisabled();
  }

  function updateDisabled() {
    const busy = consoleBusy || bluetoothBusy;
    consoleButton.disabled = busy || consoleState === "unavailable";
    bluetoothButton.disabled = busy;
  }

  function showBluetoothStatus(message, state = "") {
    bluetoothStatus.textContent = message;
    bluetoothStatus.dataset.state = state;
  }

  async function refresh() {
    if (consoleBusy || bluetoothBusy) return;
    try {
      render(await request("/api/console/status"));
    } catch (error) {
      render({ state: "unavailable", message: error.message });
    }
  }

  async function toggle() {
    if (consoleBusy || bluetoothBusy) return;
    consoleBusy = true;
    updateDisabled();
    consoleButton.textContent = "Konsole wird umgeschaltet …";
    try {
      render(await request("/api/console/toggle", {
        method: "POST",
        body: "{}",
      }));
      window.setTimeout(refresh, 1500);
    } catch (error) {
      render({ state: "unavailable", message: error.message });
    } finally {
      consoleBusy = false;
      updateDisabled();
    }
  }

  async function connectBluetooth() {
    if (consoleBusy || bluetoothBusy) return;
    window.clearTimeout(bluetoothResetTimer);
    bluetoothBusy = true;
    updateDisabled();
    bluetoothButton.textContent = "Controller werden gesucht …";
    showBluetoothStatus("Controller jetzt in den Pairing-Modus setzen.");
    try {
      const payload = await request("/api/console/bluetooth", {
        method: "POST",
        body: "{}",
      });
      bluetoothButton.textContent = "Controller verbunden";
      showBluetoothStatus(payload.message || "Bluetooth-Controller ist verbunden.", "success");
    } catch (error) {
      bluetoothButton.textContent = "Erneut versuchen";
      showBluetoothStatus(error.message, "error");
    } finally {
      bluetoothBusy = false;
      updateDisabled();
      bluetoothResetTimer = window.setTimeout(() => {
        bluetoothButton.textContent = "Bluetooth-Controller verbinden";
        showBluetoothStatus("");
      }, 8000);
    }
  }

  consoleButton.addEventListener("click", toggle);
  bluetoothButton.addEventListener("click", connectBluetooth);
  refresh();
  window.setInterval(refresh, 10000);
})();
