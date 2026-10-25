"use strict";

const byId = (id) => document.getElementById(id);
const elements = {
  body: document.body,
  live: byId("live"),
  streamEmpty: byId("streamEmpty"),
  streamStatus: byId("streamStatus"),
  streamStatusText: byId("streamStatusText"),
  streamStatusShort: byId("streamStatusShort"),
  streamEmptyTitle: byId("streamEmptyTitle"),
  streamEmptyText: byId("streamEmptyText"),
  infobar: byId("infobar"),
  clockbar: byId("clockbar"),
  clockMain: byId("clockMain"),
  clock: byId("clock"),
  date: byId("date"),
  weather: byId("weather"),
  weatherText: byId("weatherText"),
  weatherIcon: byId("weatherIcon"),
  weatherTemp: byId("weatherTemp"),
  weatherCondition: byId("weatherCondition"),
  weatherDetails: byId("weatherDetails"),
  weatherError: byId("weatherError"),
  rainLabel: byId("rainLabel"),
  rainSummary: byId("rainSummary"),
  rainHours: byId("rainHours"),
  sysbar: byId("sysbar"),
  sys: byId("sys"),
  radar: byId("radar"),
  radarBox: byId("radarBox"),
  radarMap: byId("radarMap"),
  radarLabel: byId("radarLabel"),
  radarTime: byId("radarTime"),
  radarStatus: byId("radarStatus"),
  radarAttribution: byId("radarAttribution"),
  transitPanel: byId("transitPanel"),
  boards: byId("boards"),
  hotspot: byId("adminHotspot"),
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
let runtimeConfig = null;
let lastState = null;
let lastRadarTime = "";
let radarSignature = "";
let backendDown = false;
let streamView = { state: "loading", full: "Lokales Backend wird geladen", short: "Wird geladen", card: null };

const NARROW_WIDTH = 760;
const RAIN_NOW_CODES = new Set([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]);
const SVG_NS = "http://www.w3.org/2000/svg";
// Wettersymbole im 24er-Raster; Farben kommen über Klassen aus dem CSS (CSP erlaubt keine Inline-Styles).
const CLOUD = "M7 18.5h10.5a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.4 11.1 3.7 3.7 0 0 0 7 18.5z";
const SUN_RAYS = "M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4";
const SMALL_SUN = '<g class="wi-sun"><circle cx="7" cy="7" r="2.4"/><path d="M7 1.8v1.3M1.8 7h1.3M3.3 3.3l.9.9M10.7 3.3l-.9.9M3.3 10.7l.9-.9"/></g>';
const WEATHER_ICONS = {
  sun: `<g class="wi-sun"><circle cx="12" cy="12" r="4"/><path d="${SUN_RAYS}"/></g>`,
  partly: `${SMALL_SUN}<path class="wi-cloud" transform="translate(1.5 2)" d="${CLOUD}"/>`,
  cloudy: `<path class="wi-cloud" d="${CLOUD}"/>`,
  fog: `<path class="wi-cloud" transform="translate(0 -4)" d="${CLOUD}"/><path class="wi-fog" d="M4.5 18.5h15M6.5 21.5h11"/>`,
  rain: `<path class="wi-cloud" transform="translate(0 -4)" d="${CLOUD}"/><path class="wi-drop" d="M8.5 17.5l-1 3M12.5 17.5l-1 3M16.5 17.5l-1 3"/>`,
  showers: `${SMALL_SUN}<path class="wi-cloud" transform="translate(1.5 1.5)" d="${CLOUD}"/><path class="wi-drop" d="M11 21l-.7 2.2M15.5 21l-.7 2.2"/>`,
  snow: `<path class="wi-cloud" transform="translate(0 -4)" d="${CLOUD}"/><path class="wi-snow" d="M8.5 18.5h.01M12 20.5h.01M15.5 18.5h.01M10 22h.01M14 22h.01"/>`,
  thunder: `<path class="wi-cloud" transform="translate(0 -4)" d="${CLOUD}"/><path class="wi-bolt" d="M12.8 15.5l-2.6 3.8h3.4l-2.4 3.7"/>`,
};
const ERROR_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9.5"/><path d="M12 7v6.2M12 16.8h.01"/></svg>';

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
  const weekday = elements.body.dataset.layout === "minimal" ? "short" : "long";
  elements.date.textContent = new Intl.DateTimeFormat("de-DE", { weekday, day: "numeric", month: "long" }).format(now);
}

function isMinimal() {
  return elements.body.dataset.layout === "minimal";
}

function isNarrow() {
  return window.innerWidth < NARROW_WIDTH;
}

function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", timeZone: runtimeTimezone }).format(date);
}

function hourOf(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "–";
  const parts = new Intl.DateTimeFormat("de-DE", { hour: "numeric", hourCycle: "h23", timeZone: runtimeTimezone }).formatToParts(date);
  return String(Number(parts.find((part) => part.type === "hour")?.value ?? NaN));
}

function updateInfobar() {
  const ui = runtimeConfig?.ui || {};
  const showClock = !!ui.clock?.enabled;
  const showSystem = !!ui.system?.enabled;
  elements.clockMain.classList.toggle("hidden", !showClock);
  elements.sysbar.classList.toggle("hidden", !showSystem);
  const blocks = [
    // Lange Datumsangaben („Donnerstag, 30. September“) dürfen die Uhrspalte über die Mindestbreite hinaus verbreitern.
    [elements.clockbar, showClock || showSystem, "minmax(var(--col-clock), max-content)"],
    [elements.weather, !!ui.weather?.enabled, "minmax(0, 1fr)"],
    [elements.radar, !!ui.radar?.enabled && !isNarrow(), "var(--col-radar)"],
    [elements.transitPanel, !!ui.transit?.enabled, "var(--col-transit)"],
  ];
  const tracks = [];
  blocks.forEach(([block, visible, track]) => {
    block.classList.toggle("hidden", !visible);
    const separator = block.previousElementSibling?.classList.contains("ib-sep") ? block.previousElementSibling : null;
    separator?.classList.add("hidden");
    if (!visible) return;
    if (tracks.length && separator) {
      separator.classList.remove("hidden");
      tracks.push("1px");
    }
    tracks.push(track);
  });
  // Ohne Wetterspalte gibt es keine flexible Spalte; dann wächst die letzte sichtbare.
  if (!ui.weather?.enabled && tracks.length) tracks[tracks.length - 1] = `minmax(${tracks.at(-1)}, 1fr)`;
  elements.infobar.classList.toggle("hidden", !tracks.length);
  elements.body.classList.toggle("no-infobar", !tracks.length);
  elements.infobar.style.gridTemplateColumns = tracks.join(" ");
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
  runtimeConfig = runtime;
  runtimeTimezone = runtime.timezone || runtime.app?.timezone || "Europe/Berlin";
  elements.body.dataset.theme = ui.theme || "dark";
  const layout = resolveLayout(ui.layout_profile || "auto");
  if (elements.body.dataset.layout !== layout) {
    elements.body.dataset.layout = layout;
    updateClock();
  }
  const radar = ui.radar || {};
  document.documentElement.style.setProperty("--radar-width", `${Number(radar.width || 280)}px`);
  document.documentElement.style.setProperty("--radar-height", `${Number(radar.height || 190)}px`);
  document.documentElement.style.setProperty("--radar-opacity", String(Number(radar.opacity ?? 0.92)));
  updateInfobar();
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

function renderStreamView(view) {
  elements.streamStatus.dataset.state = view.state;
  elements.streamStatusText.textContent = view.full;
  elements.streamStatusShort.textContent = view.short;
  elements.streamStatus.title = view.full;
  elements.streamEmpty.classList.toggle("has-stream", !view.card);
  if (view.card) {
    elements.streamEmptyTitle.textContent = view.card.title;
    elements.streamEmptyText.textContent = view.card.text;
  }
}

function setStreamView(view) {
  streamView = view;
  if (!backendDown) renderStreamView(view);
}

function configureStream(stream, force = false) {
  const signature = JSON.stringify({ url: stream.url || "", autoplay: !!stream.autoplay, muted: !!stream.muted });
  if (!force && signature === streamSignature) return;
  streamSignature = signature;
  const url = effectiveStreamUrl(stream);
  if (!url) {
    elements.live.removeAttribute("src");
    setStreamView({
      state: "error",
      full: "Keine Stream-URL konfiguriert",
      short: "Kein Stream",
      card: { title: "Kein Livestream konfiguriert", text: "Öffne den lokalen Adminmodus und hinterlege eine unterstützte Embed-URL." },
    });
    return;
  }
  setStreamView({ state: "loading", full: "Stream-Seite wird geladen", short: "Stream wird geladen", card: null });
  elements.live.src = "about:blank";
  requestAnimationFrame(() => { elements.live.src = url; });
}

function formatMaybe(value, suffix = "") {
  return value === null || value === undefined ? "–" : `${value}${suffix}`;
}

function renderSystem(system) {
  if (!system || system.enabled === false) return;
  const parts = [`CPU ${formatMaybe(system.cpu, " %")}`];
  if (!isMinimal()) parts.push(`RAM ${formatMaybe(system.ram, " %")}`);
  parts.push(`${formatMaybe(system.temp)} °C`);
  elements.sys.textContent = parts.join(" · ");
}

function weatherKind(code) {
  if (code === 0 || code === 1) return "sun";
  if (code === 2) return "partly";
  if (code === 45 || code === 48) return "fog";
  if (code >= 51 && code <= 67) return "rain";
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "snow";
  if (code >= 80 && code <= 82) return "showers";
  if (code >= 95 && code <= 99) return "thunder";
  return "cloudy";
}

function weatherIcon(code) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("focusable", "false");
  svg.innerHTML = WEATHER_ICONS[weatherKind(Number(code))];
  return svg;
}

function capitalize(text) {
  const value = String(text || "");
  return value ? value[0].toLocaleUpperCase("de-DE") + value.slice(1) : "";
}

function rainSummary(weather, forecast) {
  const minimal = isMinimal();
  if (weather.stale) {
    const time = formatTime(weather.updated_at);
    return { text: time ? `Stand ${time} · offline` : "offline", alert: true };
  }
  const code = Number(weather.code);
  if (Number(weather.rain) > 0 || RAIN_NOW_CODES.has(code)) {
    const dry = forecast.find((item) => !item.rainy);
    if (dry && !minimal) return { text: `Regen jetzt · trocken ab etwa ${hourOf(dry.time)} Uhr`, alert: true };
    return { text: "Regen jetzt", alert: true };
  }
  const rainy = forecast.find((item) => item.rainy);
  if (rainy) {
    const text = `ab ${hourOf(rainy.time)} Uhr · ${rainy.probability} %`;
    return { text: minimal ? text : `Regen ${text}`, alert: true };
  }
  if (!forecast.length) return { text: "", alert: false };
  const hours = forecast.length === 1 ? "Stunde" : `${forecast.length} Stunden`;
  return { text: minimal ? `kein Regen · ${forecast.length} h` : `Kein Regen in den nächsten ${hours}`, alert: false };
}

function renderRainHours(forecast) {
  const columns = forecast.slice(0, isMinimal() ? 6 : 8).map((item) => {
    const column = document.createElement("div");
    column.className = `rain-col${item.rainy ? " is-rain" : ""}`;
    const track = document.createElement("span");
    track.className = "rain-track";
    const bar = document.createElement("span");
    bar.className = "rain-bar";
    bar.style.height = `${Math.min(100, Math.max(0, Number(item.probability) || 0))}%`;
    track.append(bar);
    const hour = document.createElement("span");
    hour.className = "rain-hour";
    hour.textContent = hourOf(item.time);
    column.append(track, hour);
    return column;
  });
  elements.rainHours.replaceChildren(...columns);
}

function renderWeather(weather) {
  if (!weather) return;
  elements.weatherText.textContent = weather.text || "Wetter nicht verfügbar";
  elements.weather.classList.toggle("provider-error", !weather.ok);
  const failed = weather.ok === false && !!weather.error;
  elements.weather.classList.toggle("is-error", failed);
  if (failed) {
    elements.weatherError.textContent = weather.error;
    return;
  }
  if (!weather.ok) {
    elements.weatherIcon.replaceChildren();
    elements.weatherTemp.textContent = "–°";
    elements.weatherCondition.textContent = weather.text || "Wetter wird geladen";
    elements.weatherDetails.textContent = "";
    elements.rainSummary.textContent = "";
    elements.rainHours.replaceChildren();
    return;
  }
  elements.weatherIcon.replaceChildren(weatherIcon(weather.code));
  elements.weatherTemp.textContent = `${formatMaybe(weather.temp)}°`;
  elements.weatherCondition.textContent = capitalize(weather.condition) || "Aktuell";
  const details = [];
  if (weather.feels != null) details.push(`gefühlt ${weather.feels}°`);
  if (weather.wind != null) details.push(`Wind ${weather.wind} km/h`);
  if (weather.hum != null && !isMinimal()) details.push(`${weather.hum} %`);
  elements.weatherDetails.textContent = details.join(" · ");
  const forecast = Array.isArray(weather.forecast) ? weather.forecast : [];
  elements.rainLabel.textContent = isMinimal() ? "Regen" : "Regenwahrscheinlichkeit";
  const summary = rainSummary(weather, forecast);
  elements.rainSummary.textContent = summary.text;
  elements.rainSummary.classList.toggle("is-alert", summary.alert);
  renderRainHours(forecast);
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
  // Die OSM-Kachelrichtlinie verlangt einen Referer; die Seite selbst sendet sonst keinen.
  if (!rain) image.referrerPolicy = "origin";
  image.src = src;
  image.addEventListener("error", () => image.classList.add("tile-error"));
  return image;
}

function renderRadar(radar) {
  if (!radar) return;
  elements.radarLabel.textContent = radar.label || "Standort";
  elements.radarStatus.textContent = radar.status || "Datenstatus unbekannt";
  const online = !!(radar.ok && radar.tile_url);
  const offline = !online && (radar.offline === true || !!radar.error);
  if (online && radar.data_time) lastRadarTime = radar.data_time;
  elements.radarTime.textContent = online ? formatTime(radar.data_time) || "–" : offline ? "offline" : "wird geladen";
  elements.radarBox.classList.toggle("is-offline", offline);
  const width = elements.radarMap.clientWidth || 148;
  const height = elements.radarMap.clientHeight || 114;
  const zoom = Number(radar.zoom || 10);
  // Nur neu aufbauen, wenn sich Daten oder Größe ändern; sonst flackern die Kacheln alle 5 Sekunden.
  const signature = JSON.stringify([online, offline, radar.tile_url, zoom, radar.latitude, radar.longitude, width, height, offline ? lastRadarTime : ""]);
  if (signature === radarSignature) return;
  radarSignature = signature;
  elements.radarMap.replaceChildren();
  if (!online) {
    const message = document.createElement("span");
    message.className = "radar-message";
    const title = document.createElement("strong");
    title.textContent = offline ? "Keine Radardaten" : "Radardaten werden geladen";
    message.append(title);
    if (offline && lastRadarTime) {
      const last = document.createElement("span");
      last.textContent = `zuletzt ${formatTime(lastRadarTime)}`;
      message.append(last);
    }
    elements.radarMap.append(message);
    return;
  }
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

function parseMinutes(row) {
  if (Number.isFinite(row.minutes)) return row.minutes;
  if (row.minutes === null) return null;
  const text = String(row.mins || "");
  if (text === "jetzt") return 0;
  const hours = text.match(/^(\d+)h (\d+)$/);
  if (hours) return Number(hours[1]) * 60 + Number(hours[2]);
  const minutes = text.match(/^(\d+) min$/);
  return minutes ? Number(minutes[1]) : null;
}

function textElement(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
}

function departureRow(row) {
  const departure = document.createElement("div");
  departure.className = "departure";
  const main = document.createElement("span");
  main.className = "departure-main";
  main.append(textElement("span", "departure-target", row.target), textElement("span", "departure-sub", `ab ${row.board}`));
  const time = document.createElement("span");
  time.className = "departure-time";
  const minutes = row.sortMinutes;
  if (minutes !== null && minutes <= 0) {
    time.append(textElement("span", "departure-now", "jetzt"));
  } else if (minutes !== null && minutes < 60) {
    time.append(textElement("span", "departure-num", String(minutes)), textElement("span", "departure-unit", "min"));
  } else {
    time.append(textElement("span", "departure-num", row.mins || "–"));
  }
  departure.append(textElement("span", "departure-line", row.line), main, time);
  return departure;
}

function boardErrorRow(board) {
  const row = document.createElement("div");
  row.className = "departure is-error";
  if (board.error) row.title = board.error;
  const icon = document.createElement("span");
  icon.className = "departure-icon";
  icon.innerHTML = ERROR_ICON;
  const main = document.createElement("span");
  main.className = "departure-main";
  main.append(
    textElement("span", "departure-error", `${board.title}: VRR antwortet nicht`),
    textElement("span", "departure-sub", `letzte Abfrage ${formatTime(board.checked_at) || "–"} · neuer Versuch läuft`),
  );
  row.append(icon, main);
  return row;
}

function boardMessage(title, text = "") {
  const message = document.createElement("p");
  message.className = "board-message";
  message.append(textElement("strong", "", title));
  if (text) message.append(textElement("span", "", text));
  return message;
}

function renderBoards(boards) {
  elements.boards.replaceChildren();
  const list = Array.isArray(boards) ? boards : [];
  if (runtimeConfig?.transit_stop_count === 0) {
    elements.boards.append(boardMessage("Keine Haltestellen eingerichtet", "Im Adminmodus hinzufügen"));
    return;
  }
  // Fehler zuerst, damit ein ausgefallener Abruf nicht hinter Abfahrten verschwindet.
  const errors = list.filter((board) => board.ok === false).map(boardErrorRow);
  const rows = list
    .filter((board) => board.ok !== false)
    .flatMap((board) => (board.rows || []).map((row) => ({ ...row, board: board.title, sortMinutes: parseMinutes(row) })))
    .sort((a, b) => (a.sortMinutes ?? Infinity) - (b.sortMinutes ?? Infinity))
    .map(departureRow);
  const items = [...errors, ...rows].slice(0, isNarrow() ? 2 : 3);
  if (!items.length) {
    elements.boards.append(boardMessage("Keine passenden Abfahrten"));
    return;
  }
  elements.boards.append(...items);
}

function renderPanels(state) {
  renderWeather(state.weather);
  renderRadar(state.radar);
  renderBoards(state.boards);
  renderSystem(state.system);
}

async function refreshState() {
  try {
    const state = await api("/api/state");
    lastState = state;
    if (backendDown) {
      backendDown = false;
      renderStreamView(streamView);
    }
    applyRuntimeConfig(state.config);
    renderPanels(state);
    elements.body.classList.remove("is-loading");
  } catch (error) {
    backendDown = true;
    const showCard = !!streamView.card || !elements.live.getAttribute("src");
    renderStreamView({
      state: "error",
      full: "Lokales Backend nicht erreichbar",
      short: "Backend offline",
      card: showCard ? { title: "Lokales Backend nicht erreichbar", text: "Die Anzeige fragt alle 5 Sekunden automatisch erneut an." } : null,
    });
    elements.weatherText.textContent = "Wetterdaten nicht erreichbar";
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
  setStreamView({ state: "loaded", full: "Stream-Seite geladen · Wiedergabe nicht verifizierbar", short: "Stream-Seite geladen", card: null });
});
elements.live.addEventListener("error", () => {
  setStreamView({
    state: "error",
    full: "Stream-Einbettung möglicherweise blockiert",
    short: "Stream-Fehler",
    card: { title: "Stream nicht erreichbar", text: "Die Stream-Seite meldet einen Fehler. Die Einbettung ist möglicherweise blockiert." },
  });
});
byId("streamReload").addEventListener("click", () => {
  if (runtimeConfig?.stream) configureStream(runtimeConfig.stream, true);
  refreshState();
});
byId("reloadStreamPanel").addEventListener("click", () => configureStream(collectConfig().stream, true));

elements.hotspot.addEventListener("pointerdown", beginLongPress);
elements.hotspot.addEventListener("pointerup", cancelLongPress);
elements.hotspot.addEventListener("pointercancel", cancelLongPress);
elements.hotspot.addEventListener("pointerleave", cancelLongPress);
elements.hotspot.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") beginAdmin(elements.hotspot);
});
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
  const requested = currentConfig?.ui?.layout_profile || runtimeConfig?.ui?.layout_profile || "auto";
  elements.body.dataset.layout = resolveLayout(requested);
  updateInfobar();
  updateClock();
  if (lastState) renderPanels(lastState);
});
window.addEventListener("beforeunload", (event) => {
  if (dirty) { event.preventDefault(); event.returnValue = ""; }
});

updateClock();
setInterval(updateClock, 1000);
refreshState();
setInterval(refreshState, 5000);
