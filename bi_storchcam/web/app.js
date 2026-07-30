"use strict";

const byId = (id) => document.getElementById(id);
const elements = {
  body: document.body,
  live: byId("live"),
  streamEmpty: byId("streamEmpty"),
  streamStatus: byId("streamStatus"),
  streamStatusText: byId("streamStatusText"),
  clockbar: byId("clockbar"),
  clock: byId("clock"),
  date: byId("date"),
  weather: byId("weather"),
  weatherText: byId("weatherText"),
  sysbar: byId("sysbar"),
  sys: byId("sys"),
  radar: byId("radar"),
  radarMap: byId("radarMap"),
  radarLabel: byId("radarLabel"),
  radarTime: byId("radarTime"),
  radarStatus: byId("radarStatus"),
  radarAttribution: byId("radarAttribution"),
  transitPanel: byId("transitPanel"),
  boards: byId("boards"),
  hotspot: byId("adminHotspot"),
  consoleToggle: byId("consoleToggle"),
  pinDialog: byId("pinDialog"),
  pinForm: byId("pinForm"),
  pinTitle: byId("pinTitle"),
  pinHelp: byId("pinHelp"),
  pin: byId("adminPin"),
  pinConfirm: byId("adminPinConfirm"),
  pinConfirmField: byId("pinConfirmField"),
  pinStatus: byId("pinStatus"),
  submitPin: byId("submitPin"),
  settings: byId("settingsDialog"),
  settingsForm: byId("settingsForm"),
  saveState: byId("saveState"),
  stopEditor: byId("stopEditor"),
  stationResults: byId("stationResults"),
  stationSearchStatus: byId("stationSearchStatus"),
  toast: byId("toast"),
};

let token = sessionStorage.getItem("bi-storchcam-admin-token") || "";
let setupMode = false;
let currentConfig = null;
let workingStops = [];
let dirty = false;
let lastTrigger = null;
let streamSignature = "";
let longPressTimer = null;
let toastTimer = null;
let runtimeTimezone = "Europe/Berlin";
let consoleBusy = false;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = { error: `Ungültige Serverantwort (${response.status})` };
  }
  if (!response.ok) {
    const error = new Error(payload.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function setStatus(target, text, kind = "") {
  target.textContent = text;
  target.classList.remove("error", "success");
  if (kind) target.classList.add(kind);
}

function showToast(text) {
  elements.toast.textContent = text;
  elements.toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elements.toast.classList.add("hidden"), 3500);
}

function updateClock() {
  const now = new Date();
  elements.clock.textContent = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(now);
  elements.date.textContent = new Intl.DateTimeFormat("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" }).format(now);
}

function resolveLayout(requested) {
  if (requested !== "auto") return requested;
  if (window.innerWidth < 1150 || window.innerHeight < 650) return "minimal";
  if (window.innerWidth >= 1700 && window.innerHeight >= 850) return "information";
  return "standard";
}

function applyRuntimeConfig(runtime) {
  if (!runtime || !runtime.ui) return;
  const ui = runtime.ui;
  runtimeTimezone = runtime.timezone || runtime.app?.timezone || "Europe/Berlin";
  elements.body.dataset.theme = ui.theme || "dark";
  elements.body.dataset.layout = resolveLayout(ui.layout_profile || "auto");
  const radar = ui.radar || {};
  document.documentElement.style.setProperty("--radar-width", `${Number(radar.width || 280)}px`);
  document.documentElement.style.setProperty("--radar-height", `${Number(radar.height || 190)}px`);
  document.documentElement.style.setProperty("--radar-opacity", String(Number(radar.opacity ?? 0.92)));
  elements.clockbar.classList.toggle("hidden", !ui.clock?.enabled);
  elements.weather.classList.toggle("hidden", !ui.weather?.enabled);
  elements.radar.classList.toggle("hidden", !radar.enabled);
  elements.transitPanel.classList.toggle("hidden", !ui.transit?.enabled);
  elements.sysbar.classList.toggle("hidden", !ui.system?.enabled);
  configureStream(runtime.stream || {});
}

function effectiveStreamUrl(stream) {
  const raw = String(stream.url || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    url.searchParams.set("autoplay", stream.autoplay ? "1" : "0");
    url.searchParams.set("mute", stream.muted ? "1" : "0");
    url.searchParams.set("playsinline", "1");
    return url.toString();
  } catch (_error) {
    return raw;
  }
}

function configureStream(stream, force = false) {
  const signature = JSON.stringify({ url: stream.url || "", autoplay: !!stream.autoplay, muted: !!stream.muted });
  if (!force && signature === streamSignature) return;
  streamSignature = signature;
  const url = effectiveStreamUrl(stream);
  if (!url) {
    elements.live.removeAttribute("src");
    elements.streamEmpty.classList.remove("has-stream");
    elements.streamEmpty.querySelector("strong").textContent = "Kein Livestream konfiguriert";
    elements.streamStatus.dataset.state = "error";
    elements.streamStatusText.textContent = "Keine Stream-URL konfiguriert";
    return;
  }
  elements.streamEmpty.classList.add("has-stream");
  elements.streamStatus.dataset.state = "loading";
  elements.streamStatusText.textContent = "Stream-Seite wird geladen";
  elements.live.src = "about:blank";
  requestAnimationFrame(() => { elements.live.src = url; });
}

function formatMaybe(value, suffix = "") {
  return value === null || value === undefined ? "–" : `${value}${suffix}`;
}

function renderSystem(system) {
  if (!system || system.enabled === false) return;
  elements.sys.textContent = `CPU ${formatMaybe(system.cpu, "%")} · RAM ${formatMaybe(system.ram, "%")} · ${system.temp == null ? "Temperatur nicht verfügbar" : `${system.temp} °C`}`;
}

function renderWeather(weather) {
  if (!weather) return;
  elements.weatherText.textContent = weather.text || "Wetter nicht verfügbar";
  elements.weather.classList.toggle("provider-error", !weather.ok);
}

function tileCoordinates(latitude, longitude, zoom) {
  const size = 256;
  const scale = 2 ** zoom;
  const x = ((longitude + 180) / 360) * scale * size;
  const latRad = latitude * Math.PI / 180;
  const y = (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * scale * size;
  return { x, y, scale, size };
}

function tileImage(src, left, top, rain = false) {
  const image = document.createElement("img");
  image.className = `radar-tile${rain ? " radar-rain" : ""}`;
  image.alt = "";
  image.loading = "eager";
  image.style.left = `${left}px`;
  image.style.top = `${top}px`;
  image.src = src;
  image.addEventListener("error", () => image.classList.add("tile-error"));
  return image;
}

function renderRadar(radar) {
  if (!radar) return;
  elements.radarLabel.textContent = radar.label || "Standort";
  elements.radarStatus.textContent = radar.status || "Datenstatus unbekannt";
  elements.radarTime.textContent = radar.data_time ? new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", timeZone: runtimeTimezone }).format(new Date(radar.data_time)) : "offline";
  elements.radarAttribution.textContent = radar.attribution || "RainViewer · OpenStreetMap-Mitwirkende";
  elements.radarMap.replaceChildren();
  if (!radar.ok || !radar.tile_url) {
    const message = document.createElement("span");
    message.className = "loading-copy";
    message.textContent = radar.error ? `Radar offline: ${radar.error}` : "Radar offline";
    elements.radarMap.append(message);
    return;
  }
  const width = elements.radarMap.clientWidth || 280;
  const height = elements.radarMap.clientHeight || 190;
  const zoom = Number(radar.zoom || 10);
  const world = tileCoordinates(Number(radar.latitude), Number(radar.longitude), zoom);
  const leftWorld = world.x - width / 2;
  const topWorld = world.y - height / 2;
  const firstX = Math.floor(leftWorld / world.size);
  const lastX = Math.floor((leftWorld + width) / world.size);
  const firstY = Math.floor(topWorld / world.size);
  const lastY = Math.floor((topWorld + height) / world.size);
  for (let tileY = firstY; tileY <= lastY; tileY += 1) {
    if (tileY < 0 || tileY >= world.scale) continue;
    for (let tileX = firstX; tileX <= lastX; tileX += 1) {
      const wrappedX = ((tileX % world.scale) + world.scale) % world.scale;
      const left = tileX * world.size - leftWorld;
      const top = tileY * world.size - topWorld;
      const baseUrl = `https://tile.openstreetmap.org/${zoom}/${wrappedX}/${tileY}.png`;
      const rainUrl = radar.tile_url
        .replace("{z}", String(zoom))
        .replace("{x}", String(wrappedX))
        .replace("{y}", String(tileY));
      elements.radarMap.append(tileImage(baseUrl, left, top));
      elements.radarMap.append(tileImage(rainUrl, left, top, true));
    }
  }
  const marker = document.createElement("span");
  marker.className = "radar-marker";
  marker.title = radar.label || "Standort";
  elements.radarMap.append(marker);
}

function renderBoards(boards) {
  elements.boards.replaceChildren();
  if (!Array.isArray(boards) || boards.length === 0) {
    const empty = document.createElement("p");
    empty.className = "board-message";
    empty.textContent = "Keine Haltestellen oder Abfahrten verfügbar.";
    elements.boards.append(empty);
    return;
  }
  boards.forEach((board) => {
    const section = document.createElement("section");
    section.className = "board";
    const header = document.createElement("div");
    header.className = "board-title";
    header.innerHTML = `<span>${escapeHtml(board.title)}</span><span>${escapeHtml(board.ok === false ? "Fehler" : "Live")}</span>`;
    section.append(header);
    if (board.ok === false) {
      const error = document.createElement("p");
      error.className = "board-message error";
      error.textContent = board.error || "VRR-Daten derzeit nicht verfügbar.";
      section.append(error);
    } else if (!board.rows?.length) {
      const empty = document.createElement("p");
      empty.className = "board-message";
      empty.textContent = "Keine passenden Abfahrten.";
      section.append(empty);
    } else {
      board.rows.forEach((row) => {
        const departure = document.createElement("div");
        departure.className = "departure";
        departure.innerHTML = `<span class="departure-line">${escapeHtml(row.line)}</span><span class="departure-target">${escapeHtml(row.target)}</span><span class="departure-mins">${escapeHtml(row.mins)}</span>`;
        section.append(departure);
      });
    }
    elements.boards.append(section);
  });
}

async function refreshState() {
  try {
    const state = await api("/api/state");
    applyRuntimeConfig(state.config);
    renderWeather(state.weather);
    renderRadar(state.radar);
    renderBoards(state.boards);
    renderSystem(state.system);
    elements.body.classList.remove("is-loading");
  } catch (error) {
    elements.streamStatus.dataset.state = "error";
    elements.streamStatusText.textContent = "Lokales Backend nicht erreichbar";
    elements.weatherText.textContent = "Wetterdaten nicht erreichbar";
  }
}

function renderConsoleStatus(payload) {
  const state = ["running", "stopped", "unavailable"].includes(payload?.state)
    ? payload.state
    : "unavailable";
  const labels = {
    running: "Pegasus läuft – antippen zum Beenden",
    stopped: "Pegasus starten",
    unavailable: payload?.message || "Pegasus ist nicht verfügbar",
  };
  elements.consoleToggle.dataset.state = state;
  elements.consoleToggle.setAttribute("aria-label", labels[state]);
  elements.consoleToggle.title = labels[state];
}

async function refreshConsoleStatus() {
  if (consoleBusy) return;
  try {
    renderConsoleStatus(await api("/api/console"));
  } catch (error) {
    renderConsoleStatus({ state: "unavailable", message: error.message });
  }
}

async function toggleConsole() {
  if (consoleBusy) return;
  consoleBusy = true;
  elements.consoleToggle.disabled = true;
  elements.consoleToggle.dataset.state = "busy";
  elements.consoleToggle.setAttribute("aria-label", "Pegasus wird umgeschaltet");
  elements.consoleToggle.title = "Pegasus wird umgeschaltet";
  try {
    const result = await api("/api/console/toggle", {
      method: "POST",
      body: JSON.stringify({}),
    });
    renderConsoleStatus(result);
    showToast(result.state === "running" ? "Pegasus startet auf HDMI" : "Pegasus wurde beendet");
  } catch (error) {
    renderConsoleStatus({ state: "unavailable", message: error.message });
    showToast(`Pegasus nicht verfügbar: ${error.message}`);
  } finally {
    consoleBusy = false;
    elements.consoleToggle.disabled = false;
  }
}

function openDialog(dialog, trigger) {
  lastTrigger = trigger || document.activeElement;
  if (!dialog.open) dialog.showModal();
}

function closeDialog(dialog) {
  if (dialog.open) dialog.close();
  if (lastTrigger instanceof HTMLElement) lastTrigger.focus();
}

function trapFocus(dialog, event) {
  if (event.key !== "Tab") return;
  const focusable = [...dialog.querySelectorAll("button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])")]
    .filter((item) => !item.closest(".hidden"));
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

async function beginAdmin(trigger) {
  try {
    if (token) {
      await loadConfig();
      openDialog(elements.settings, trigger);
      return;
    }
    const status = await api("/api/admin/status");
    setupMode = !status.pin_configured;
    elements.pinTitle.textContent = setupMode ? "Admin-PIN erstmals festlegen" : "Admin-PIN eingeben";
    elements.pinHelp.textContent = setupMode
      ? "Die PIN wird nur als sicherer Hash auf diesem Gerät gespeichert."
      : "Die lokale Admin-Sitzung ist zeitlich begrenzt.";
    elements.pinConfirmField.classList.toggle("hidden", !setupMode);
    elements.pinConfirm.required = setupMode;
    elements.submitPin.textContent = setupMode ? "PIN festlegen" : "Anmelden";
    elements.pin.value = "";
    elements.pinConfirm.value = "";
    setStatus(elements.pinStatus, "");
    openDialog(elements.pinDialog, trigger);
    elements.pin.focus();
  } catch (error) {
    showToast(`Adminmodus nicht verfügbar: ${error.message}`);
  }
}

async function authenticate(event) {
  event.preventDefault();
  const pin = elements.pin.value.trim();
  if (setupMode && pin !== elements.pinConfirm.value.trim()) {
    setStatus(elements.pinStatus, "Die PINs stimmen nicht überein.", "error");
    return;
  }
  elements.submitPin.disabled = true;
  setStatus(elements.pinStatus, setupMode ? "PIN wird sicher gespeichert …" : "Anmeldung läuft …");
  try {
    const result = await api(setupMode ? "/api/admin/setup" : "/api/admin/login", {
      method: "POST",
      body: JSON.stringify({ pin }),
    });
    token = result.token;
    sessionStorage.setItem("bi-storchcam-admin-token", token);
    await loadConfig();
    closeDialog(elements.pinDialog);
    openDialog(elements.settings, elements.hotspot);
  } catch (error) {
    setStatus(elements.pinStatus, error.message, "error");
  } finally {
    elements.submitPin.disabled = false;
  }
}

function fillForm(config) {
  byId("cfgStream").value = config.stream.url || "";
  byId("streamAutoplay").checked = !!config.stream.autoplay;
  byId("streamMuted").checked = !!config.stream.muted;
  byId("cfgLabel").value = config.location.label || "";
  byId("cfgLat").value = config.location.latitude;
  byId("cfgLon").value = config.location.longitude;
  byId("cfgLayout").value = config.ui.layout_profile;
  byId("cfgTheme").value = config.ui.theme;
  byId("cfgRadarOpacity").value = config.ui.radar.opacity;
  byId("cfgRadarW").value = config.ui.radar.width;
  byId("cfgRadarH").value = config.ui.radar.height;
  byId("showClock").checked = !!config.ui.clock.enabled;
  byId("showWeather").checked = !!config.ui.weather.enabled;
  byId("showRadar").checked = !!config.ui.radar.enabled;
  byId("showTransit").checked = !!config.ui.transit.enabled;
  byId("showSystem").checked = !!config.ui.system.enabled;
  workingStops = clone(config.transit.stops || []);
  renderStopEditor();
  dirty = false;
  setStatus(elements.saveState, "");
}

async function loadConfig() {
  try {
    const result = await api("/api/config");
    currentConfig = result.config;
    fillForm(currentConfig);
  } catch (error) {
    if (error.status === 401) {
      token = "";
      sessionStorage.removeItem("bi-storchcam-admin-token");
    }
    throw error;
  }
}

function renderStopEditor() {
  elements.stopEditor.replaceChildren();
  if (!workingStops.length) {
    const empty = document.createElement("p");
    empty.className = "board-message";
    empty.textContent = "Noch keine Haltestelle konfiguriert. Die ÖPNV-Anzeige bleibt leer.";
    elements.stopEditor.append(empty);
    return;
  }
  workingStops.forEach((stop, index) => {
    const card = document.createElement("article");
    card.className = "stop-card";
    card.dataset.index = String(index);
    card.innerHTML = `
      <header class="stop-card-header">
        <strong>${escapeHtml(stop.title || stop.station_name || `Haltestelle ${index + 1}`)}</strong>
        <div class="stop-actions">
          <button class="button button-secondary" type="button" data-action="up" aria-label="Haltestelle nach oben" ${index === 0 ? "disabled" : ""}>↑</button>
          <button class="button button-secondary" type="button" data-action="down" aria-label="Haltestelle nach unten" ${index === workingStops.length - 1 ? "disabled" : ""}>↓</button>
          <button class="button button-danger" type="button" data-action="remove">Löschen</button>
        </div>
      </header>
      <div class="stop-fields">
        <label class="field wide"><span>Anzeigename</span><input name="title" value="${escapeHtml(stop.title || "")}" maxlength="80"></label>
        <label class="field wide"><span>Haltestellenname</span><input name="station_name" value="${escapeHtml(stop.station_name || "")}" maxlength="160" required></label>
        <label class="field"><span>Haltestellen-ID</span><input name="station_id" value="${escapeHtml(stop.station_id || "")}" maxlength="80"></label>
        <label class="field"><span>Linienfilter (Komma)</span><input name="line_filter" value="${escapeHtml((stop.line_filter || []).join(", "))}" maxlength="160"></label>
        <label class="field"><span>Maximale Zeilen</span><input name="max_rows" type="number" min="1" max="12" value="${Number(stop.max_rows || 2)}"></label>
        <label class="toggle"><input name="nightbus_only" type="checkbox" ${stop.nightbus_only ? "checked" : ""}><span>Nur Nachtbus</span></label>
        <label class="toggle"><input name="hide_if_empty" type="checkbox" ${stop.hide_if_empty ? "checked" : ""}><span>Leer ausblenden</span></label>
      </div>`;
    elements.stopEditor.append(card);
  });
}

function syncStopField(input) {
  const card = input.closest(".stop-card");
  if (!card) return;
  const stop = workingStops[Number(card.dataset.index)];
  if (!stop) return;
  if (input.name === "line_filter") {
    stop.line_filter = input.value.split(",").map((item) => item.trim()).filter(Boolean);
  } else if (input.name === "max_rows") {
    stop.max_rows = Number(input.value);
  } else if (input.type === "checkbox") {
    stop[input.name] = input.checked;
  } else {
    stop[input.name] = input.value;
  }
  dirty = true;
}

function stopAction(button) {
  const card = button.closest(".stop-card");
  if (!card) return;
  const index = Number(card.dataset.index);
  if (button.dataset.action === "remove") workingStops.splice(index, 1);
  if (button.dataset.action === "up" && index > 0) [workingStops[index - 1], workingStops[index]] = [workingStops[index], workingStops[index - 1]];
  if (button.dataset.action === "down" && index < workingStops.length - 1) [workingStops[index + 1], workingStops[index]] = [workingStops[index], workingStops[index + 1]];
  dirty = true;
  renderStopEditor();
}

async function searchStations() {
  const query = byId("stationQuery").value.trim();
  if (query.length < 2) {
    setStatus(elements.stationSearchStatus, "Bitte mindestens zwei Zeichen eingeben.", "error");
    return;
  }
  byId("stationSearchBtn").disabled = true;
  setStatus(elements.stationSearchStatus, "VRR-Haltestellen werden gesucht …");
  elements.stationResults.replaceChildren();
  try {
    const result = await api(`/api/station/search?q=${encodeURIComponent(query)}`);
    if (!result.results.length) {
      setStatus(elements.stationSearchStatus, "Keine VRR-Haltestelle gefunden. Andere Schreibweise versuchen.");
      return;
    }
    setStatus(elements.stationSearchStatus, `${result.results.length} Treffer`);
    result.results.forEach((station) => {
      const row = document.createElement("div");
      row.className = "station-result";
      const name = document.createElement("span");
      name.textContent = station.station_name;
      const add = document.createElement("button");
      add.type = "button";
      add.className = "button button-secondary";
      add.textContent = "Hinzufügen";
      add.addEventListener("click", () => {
        workingStops.push({
          title: station.station_name.replace("Bielefeld", "").trim() || station.station_name,
          station_name: station.station_name,
          station_id: station.station_id,
          line_filter: [],
          nightbus_only: false,
          hide_if_empty: true,
          max_rows: Number(currentConfig.transit.default_max_rows || 2),
        });
        byId("showTransit").checked = true;
        dirty = true;
        renderStopEditor();
        showToast("Haltestelle hinzugefügt. Zum Übernehmen noch speichern.");
      });
      row.append(name, add);
      elements.stationResults.append(row);
    });
  } catch (error) {
    setStatus(elements.stationSearchStatus, `Suche fehlgeschlagen: ${error.message}`, "error");
  } finally {
    byId("stationSearchBtn").disabled = false;
  }
}

function collectConfig() {
  if (!currentConfig) throw new Error("Konfiguration ist noch nicht geladen");
  const config = clone(currentConfig);
  config.stream.url = byId("cfgStream").value.trim();
  config.stream.autoplay = byId("streamAutoplay").checked;
  config.stream.muted = byId("streamMuted").checked;
  config.location.label = byId("cfgLabel").value.trim();
  config.location.latitude = Number(byId("cfgLat").value);
  config.location.longitude = Number(byId("cfgLon").value);
  config.ui.layout_profile = byId("cfgLayout").value;
  config.ui.theme = byId("cfgTheme").value;
  config.ui.radar.opacity = Number(byId("cfgRadarOpacity").value);
  config.ui.radar.width = Number(byId("cfgRadarW").value);
  config.ui.radar.height = Number(byId("cfgRadarH").value);
  config.ui.clock.enabled = byId("showClock").checked;
  config.ui.weather.enabled = byId("showWeather").checked;
  config.ui.radar.enabled = byId("showRadar").checked;
  config.ui.transit.enabled = byId("showTransit").checked;
  config.ui.system.enabled = byId("showSystem").checked;
  config.transit.stops = clone(workingStops);
  if (!config.location.label) throw new Error("Standortname fehlt");
  if (!Number.isFinite(config.location.latitude) || !Number.isFinite(config.location.longitude)) throw new Error("Koordinaten sind ungültig");
  config.transit.stops.forEach((stop, index) => {
    if (!stop.station_id && !stop.station_name) throw new Error(`Haltestelle ${index + 1} benötigt ID oder Namen`);
    if (!Number.isInteger(stop.max_rows) || stop.max_rows < 1 || stop.max_rows > 12) throw new Error(`Maximale Zeilen bei Haltestelle ${index + 1} sind ungültig`);
  });
  return config;
}

async function saveConfig() {
  const button = byId("saveConfig");
  button.disabled = true;
  setStatus(elements.saveState, "Konfiguration wird validiert und atomar gespeichert …");
  try {
    const candidate = collectConfig();
    const result = await api("/api/config/save", { method: "POST", body: JSON.stringify({ config: candidate }) });
    currentConfig = result.config;
    fillForm(currentConfig);
    applyRuntimeConfig({ ...currentConfig, timezone: currentConfig.app?.timezone });
    setStatus(elements.saveState, "Gespeichert. Providerdaten werden im Hintergrund aktualisiert.", "success");
    showToast("Konfiguration gespeichert");
  } catch (error) {
    setStatus(elements.saveState, `Speichern fehlgeschlagen: ${error.message}`, "error");
  } finally {
    button.disabled = false;
  }
}

function requestSettingsClose() {
  if (dirty && !window.confirm("Ungespeicherte Änderungen verwerfen?")) return;
  dirty = false;
  closeDialog(elements.settings);
}

function beginLongPress(event) {
  event.preventDefault();
  clearTimeout(longPressTimer);
  longPressTimer = setTimeout(() => beginAdmin(elements.hotspot), 3000);
}

function cancelLongPress() {
  clearTimeout(longPressTimer);
  longPressTimer = null;
}

elements.live.addEventListener("load", () => {
  if (!elements.live.getAttribute("src") || elements.live.src === "about:blank") return;
  elements.streamStatus.dataset.state = "loaded";
  elements.streamStatusText.textContent = "Stream-Seite geladen · Wiedergabe nicht verifizierbar";
});
elements.live.addEventListener("error", () => {
  elements.streamStatus.dataset.state = "error";
  elements.streamStatusText.textContent = "Stream-Einbettung möglicherweise blockiert";
});
byId("streamReload").addEventListener("click", () => currentConfig ? configureStream(currentConfig.stream, true) : refreshState());
byId("reloadStreamPanel").addEventListener("click", () => configureStream(collectConfig().stream, true));

elements.hotspot.addEventListener("pointerdown", beginLongPress);
elements.hotspot.addEventListener("pointerup", cancelLongPress);
elements.hotspot.addEventListener("pointercancel", cancelLongPress);
elements.hotspot.addEventListener("pointerleave", cancelLongPress);
elements.hotspot.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") beginAdmin(elements.hotspot);
});
elements.consoleToggle.addEventListener("click", toggleConsole);
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.altKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    beginAdmin(document.activeElement);
  }
});

elements.pinForm.addEventListener("submit", authenticate);
byId("cancelPin").addEventListener("click", () => closeDialog(elements.pinDialog));
elements.pinDialog.addEventListener("keydown", (event) => trapFocus(elements.pinDialog, event));
elements.settings.addEventListener("keydown", (event) => {
  trapFocus(elements.settings, event);
  if (event.key === "Escape") {
    event.preventDefault();
    requestSettingsClose();
  }
});
elements.settings.addEventListener("cancel", (event) => { event.preventDefault(); requestSettingsClose(); });
byId("closeSettings").addEventListener("click", requestSettingsClose);
byId("saveConfig").addEventListener("click", saveConfig);
byId("reloadConfig").addEventListener("click", async () => {
  try {
    await loadConfig();
    showToast("Konfiguration neu geladen");
  } catch (error) {
    setStatus(elements.saveState, `Laden fehlgeschlagen: ${error.message}`, "error");
  }
});
elements.settingsForm.addEventListener("input", () => { dirty = true; });
elements.stopEditor.addEventListener("input", (event) => syncStopField(event.target));
elements.stopEditor.addEventListener("change", (event) => syncStopField(event.target));
elements.stopEditor.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (button) stopAction(button);
});
byId("stationSearchBtn").addEventListener("click", searchStations);
byId("stationQuery").addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); searchStations(); }
});
window.addEventListener("resize", () => {
  const requested = currentConfig?.ui?.layout_profile || "auto";
  elements.body.dataset.layout = resolveLayout(requested);
});
window.addEventListener("beforeunload", (event) => {
  if (dirty) { event.preventDefault(); event.returnValue = ""; }
});

updateClock();
setInterval(updateClock, 1000);
refreshState();
setInterval(refreshState, 5000);
refreshConsoleStatus();
setInterval(refreshConsoleStatus, 5000);
