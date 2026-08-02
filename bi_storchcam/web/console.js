"use strict";

(() => {
  const button = document.getElementById("consoleToggle");
  if (!button) return;

  let busy = false;

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
    button.dataset.state = state;
    button.classList.toggle("button-danger", state === "running");
    button.classList.toggle("button-secondary", state !== "running");

    if (state === "running") {
      button.textContent = "Konsole beenden";
      button.title = "KonsolenDocker auf dem HDMI-Bildschirm beenden";
      button.disabled = busy;
      return;
    }
    if (state === "stopped") {
      button.textContent = "Konsole starten";
      button.title = "KonsolenDocker auf dem HDMI-Bildschirm starten";
      button.disabled = busy;
      return;
    }

    button.textContent = "Konsole nicht bereit";
    button.title = payload?.message || "KonsolenDocker ist auf diesem Gerät nicht verfügbar";
    button.disabled = true;
  }

  async function refresh() {
    if (busy) return;
    try {
      render(await request("/api/console/status"));
    } catch (error) {
      render({ state: "unavailable", message: error.message });
    }
  }

  async function toggle() {
    if (busy) return;
    busy = true;
    button.disabled = true;
    button.textContent = "Konsole wird umgeschaltet …";
    try {
      render(await request("/api/console/toggle", {
        method: "POST",
        body: "{}",
      }));
      window.setTimeout(refresh, 1500);
    } catch (error) {
      render({ state: "unavailable", message: error.message });
    } finally {
      busy = false;
    }
  }

  button.addEventListener("click", toggle);
  refresh();
  window.setInterval(refresh, 10000);
})();
