"use strict";

const byId = (id) => document.getElementById(id);
const elements = {
  body: document.body,
  live: byId("live"),
  streamEmpty: byId("streamEmpty"),
  streamStatus: byId("streamStatus"),
  streamStatusText: byId("streamStatusText"),
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
  settingsShell: document.querySelector(".settings-shell"),
  liveQuery: byId("liveQuery"),
  liveStatus: byId("liveStatus"),
  liveResults: byId("liveResults"),
  liveCurrent: byId("liveCurrent"),
  placeQuery: byId("placeQuery"),
  placeStatus: byId("placeStatus"),
  placeResults: byId("placeResults"),
  placeCurrent: byId("placeCurrent"),
  youtubeKeyState: byId("youtubeKeyState"),
  osk: byId("osk"),
};

let token = sessionStorage.getItem("bi-storchcam-admin-token") || "";
let setupMode = false;
let currentConfig = null;
let workingStops = [];
let dirty = false;
let lastTrigger = null;
let streamSignature = "";
let toastTimer = null;
let runtimeTimezone = "Europe/Berlin";
let youtubeKeySet = false;
let pendingTimezone = "";
let liveTitle = "";
let liveLoadedOnce = false;
let oskTarget = null;
let oskShift = false;
let runtimeConfig = null;
let lastState = null;
let backendDown = false;
let streamView = { state: "loading", full: "Lokales Backend wird geladen", card: null };

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

function isMinimal() {
  return elements.body.dataset.layout === "minimal";
}

function isNarrow() {
  return window.innerWidth < NARROW_WIDTH;
}

function updateClock() {
  const now = new Date();
  // Uhr und Datum in der Zeitzone des gewählten Orts, nicht der des Geräts.
  const timeZone = runtimeTimezone;
  elements.clock.textContent = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", timeZone }).format(now);
  const weekday = isMinimal() ? "short" : "long";
  elements.date.textContent = new Intl.DateTimeFormat("de-DE", { weekday, day: "numeric", month: "long", timeZone }).format(now);
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
      card: { title: "Kein Livestream konfiguriert", text: "Öffne den lokalen Adminmodus und hinterlege eine unterstützte Embed-URL." },
    });
    return;
  }
  setStreamView({ state: "loading", full: "Stream-Seite wird geladen", card: null });
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
      openMenu(trigger);
      return;
    }
    const status = await api("/api/admin/status");
    if (status.pin_required === false) {
      await loadConfig();
      openMenu(trigger);
      return;
    }
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
    openMenu(elements.hotspot);
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
  byId("showClock").checked = !!config.ui.clock.enabled;
  byId("showWeather").checked = !!config.ui.weather.enabled;
  byId("showTransit").checked = !!config.ui.transit.enabled;
  byId("showSystem").checked = !!config.ui.system.enabled;
  byId("cfgYoutubeKey").value = "";
  byId("cfgYoutubeQuery").value = config.youtube?.default_query ?? "Storch";
  elements.youtubeKeyState.textContent = youtubeKeySet
    ? "Ein Schlüssel ist hinterlegt; die Suche nutzt die offizielle YouTube-API. Zum Ersetzen neuen Schlüssel eintragen und speichern."
    : "Kein Schlüssel nötig: Die Suche liest die öffentliche YouTube-Suche mit dem Filter „Live“. Ein eigener Schlüssel ist optional.";
  elements.placeCurrent.textContent = `${config.location.label} (${config.app?.timezone || runtimeTimezone})`;
  elements.liveCurrent.textContent = liveTitle || config.stream.url || "kein Stream";
  pendingTimezone = "";
  workingStops = clone(config.transit.stops || []);
  renderStopEditor();
  dirty = false;
  setStatus(elements.saveState, "");
}

async function loadConfig() {
  try {
    const result = await api("/api/config");
    youtubeKeySet = !!result.youtube_key_set;
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
  config.ui.clock.enabled = byId("showClock").checked;
  config.ui.weather.enabled = byId("showWeather").checked;
  config.ui.transit.enabled = byId("showTransit").checked;
  config.ui.system.enabled = byId("showSystem").checked;
  config.transit.stops = clone(workingStops);
  if (config.youtube) {
    config.youtube.api_key = byId("cfgYoutubeKey").value.trim();
    config.youtube.default_query = byId("cfgYoutubeQuery").value.trim();
  }
  if (pendingTimezone) config.app.timezone = pendingTimezone;
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
    if (candidate.youtube?.api_key) youtubeKeySet = true;
    currentConfig = result.config;
    fillForm(currentConfig);
    applyRuntimeConfig({ ...currentConfig, timezone: currentConfig.app?.timezone });
    setStatus(elements.saveState, "Gespeichert. Providerdaten werden im Hintergrund aktualisiert.", "success");
    showToast("Konfiguration gespeichert");
    return true;
  } catch (error) {
    setStatus(elements.saveState, `Speichern fehlgeschlagen: ${error.message}`, "error");
    return false;
  } finally {
    button.disabled = false;
  }
}

function showTab(name) {
  document.querySelectorAll(".menu-tab").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === name)));
  document.querySelectorAll(".menu-panel").forEach((panel) => { panel.hidden = panel.dataset.panel !== name; });
  hideKeyboard();
  if (name === "live" && !liveLoadedOnce) searchLive(byId("cfgYoutubeQuery").value.trim() || "Storch");
}

function openMenu(trigger) {
  openDialog(elements.settings, trigger);
  showTab("live");
}

async function searchLive(query) {
  liveLoadedOnce = true;
  elements.liveQuery.value = query;
  elements.liveResults.replaceChildren();
  byId("liveSearchBtn").disabled = true;
  setStatus(elements.liveStatus, `Suche Live-Streams zu „${query || "alles"}“ …`);
  try {
    const result = await api(`/api/live/search?q=${encodeURIComponent(query)}`);
    if (!result.results.length) {
      setStatus(elements.liveStatus, "Gerade ist dazu nichts live. Anderes Suchwort versuchen.");
      return;
    }
    setStatus(elements.liveStatus, `${result.results.length} Live-Streams – zum Abspielen antippen`);
    const current = byId("cfgStream").value.trim();
    result.results.forEach((video) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = `live-card${current === video.embed_url ? " is-current" : ""}`;
      const image = document.createElement("img");
      image.alt = "";
      image.loading = "lazy";
      image.src = video.thumbnail;
      card.append(image, textElement("span", "live-badge", "LIVE"), textElement("strong", "", video.title), textElement("span", "", video.channel));
      card.addEventListener("click", () => chooseLive(video));
      elements.liveResults.append(card);
    });
  } catch (error) {
    setStatus(elements.liveStatus, error.message, "error");
  } finally {
    byId("liveSearchBtn").disabled = false;
  }
}

async function chooseLive(video) {
  byId("cfgStream").value = video.embed_url;
  liveTitle = video.title;
  if (await saveConfig()) {
    showToast(`Stream gewechselt: ${video.title}`);
    dirty = false;
    closeDialog(elements.settings);
  }
}

async function searchPlaces() {
  const query = elements.placeQuery.value.trim();
  hideKeyboard();
  if (query.length < 2) {
    setStatus(elements.placeStatus, "Bitte mindestens zwei Zeichen eingeben.", "error");
    return;
  }
  byId("placeSearchBtn").disabled = true;
  setStatus(elements.placeStatus, "Orte werden gesucht …");
  elements.placeResults.replaceChildren();
  try {
    const result = await api(`/api/location/search?q=${encodeURIComponent(query)}`);
    if (!result.results.length) {
      setStatus(elements.placeStatus, "Kein Ort gefunden. Andere Schreibweise versuchen.");
      return;
    }
    setStatus(elements.placeStatus, "Ort antippen, um ihn zu übernehmen");
    result.results.forEach((place) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "place-card";
      card.append(textElement("strong", "", place.name), textElement("span", "", [place.region, place.timezone].filter(Boolean).join(" · ")));
      card.addEventListener("click", () => choosePlace(place));
      elements.placeResults.append(card);
    });
  } catch (error) {
    setStatus(elements.placeStatus, error.message, "error");
  } finally {
    byId("placeSearchBtn").disabled = false;
  }
}

async function choosePlace(place) {
  byId("cfgLabel").value = place.name;
  byId("cfgLat").value = place.latitude;
  byId("cfgLon").value = place.longitude;
  pendingTimezone = place.timezone || "";
  if (!pendingTimezone) {
    setStatus(elements.placeStatus, "Zeitzone wird ermittelt …");
    try {
      pendingTimezone = (await api(`/api/location/timezone?lat=${place.latitude}&lon=${place.longitude}`)).timezone;
    } catch (error) {
      setStatus(elements.placeStatus, `Zeitzone unbekannt, bisherige bleibt: ${error.message}`, "error");
    }
  }
  if (await saveConfig()) {
    elements.placeResults.replaceChildren();
    setStatus(elements.placeStatus, `Ort übernommen: ${place.name}. Uhr und Wetter werden aktualisiert.`, "success");
  }
}

const OSK_LAYOUTS = {
  letters: [
    ["q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "ü"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ö", "ä"],
    ["shift", "y", "x", "c", "v", "b", "n", "m", "ß", "backspace"],
    ["mode", "-", "space", ".", "enter"],
  ],
  numbers: [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["@", "/", ":", ";", "(", ")", "&", "+", "'", "\""],
    ["_", ",", "?", "!", "#", "%", "=", "backspace"],
    ["mode", "-", "space", ".", "enter"],
  ],
};
const OSK_ICONS = {
  shift: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4 4 12h4.5v7h7v-7H20z"/></svg>',
  backspace: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5h11v14H9l-6-7z"/><path d="m12.5 9.5 5 5m0-5-5 5"/></svg>',
};
const OSK_LABELS = { shift: "Großbuchstabe", backspace: "Löschen", space: "Leerzeichen" };
let oskLayout = "letters";

// „ß“.toUpperCase() ergibt „SS“; auf der Tastatur soll es einfach ß bleiben.
function oskUpper(key) {
  return key === "ß" ? key : key.toLocaleUpperCase("de-DE");
}

function buildKeyboard() {
  const handle = document.createElement("button");
  handle.type = "button";
  handle.className = "osk-close";
  handle.dataset.key = "hide";
  handle.textContent = "Tastatur schließen";
  const rows = OSK_LAYOUTS[oskLayout].map((keys) => {
    const row = document.createElement("div");
    row.className = "osk-row";
    keys.forEach((key) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `osk-key osk-${key.length === 1 ? "char" : key}`;
      button.dataset.key = key;
      if (OSK_ICONS[key]) button.innerHTML = OSK_ICONS[key];
      else if (key === "mode") button.textContent = oskLayout === "letters" ? "123" : "ABC";
      else if (key === "enter") button.textContent = oskTarget?.dataset.enter ? "Suchen" : "OK";
      else if (key === "space") button.textContent = "Leerzeichen";
      else button.textContent = oskShift ? oskUpper(key) : key;
      if (OSK_LABELS[key]) button.setAttribute("aria-label", OSK_LABELS[key]);
      if (key === "shift") button.setAttribute("aria-pressed", String(oskShift));
      row.append(button);
    });
    return row;
  });
  elements.osk.replaceChildren(handle, ...rows);
}

function setShift(value) {
  oskShift = value;
  buildKeyboard();
}

function showKeyboard(input) {
  const dialog = input.closest("dialog");
  if (!dialog) return;
  oskTarget = input;
  oskLayout = input.type === "number" || input.inputMode === "numeric" ? "numbers" : "letters";
  // Wie am Handy: im leeren Textfeld beginnt man mit einem Großbuchstaben.
  oskShift = oskLayout === "letters" && input.type !== "password" && !input.value;
  buildKeyboard();
  const host = dialog.querySelector(".settings-shell, .dialog-card") || dialog;
  if (elements.osk.parentElement !== host) host.append(elements.osk);
  elements.osk.classList.remove("hidden");
  elements.settingsShell.classList.toggle("osk-open", host === elements.settingsShell);
  input.scrollIntoView({ block: "center", behavior: "auto" });
}

function hideKeyboard() {
  oskTarget = null;
  elements.osk.classList.add("hidden");
  elements.settingsShell.classList.remove("osk-open");
}

function typeKey(key) {
  const input = oskTarget;
  if (!input) return;
  if (key === "hide") { hideKeyboard(); return; }
  if (key === "shift") { setShift(!oskShift); return; }
  if (key === "mode") {
    oskLayout = oskLayout === "letters" ? "numbers" : "letters";
    oskShift = false;
    buildKeyboard();
    return;
  }
  if (key === "enter") {
    const target = input.dataset.enter && byId(input.dataset.enter);
    hideKeyboard();
    if (target) target.click();
    return;
  }
  const character = key === "space" ? " " : (oskShift ? oskUpper(key) : key);
  // number-Felder kennen keine Cursorposition; dort wird am Ende angehängt bzw. gelöscht.
  const caret = input.type !== "number" && typeof input.selectionStart === "number";
  if (key === "backspace") {
    if (caret && input.selectionStart !== input.selectionEnd) input.setRangeText("", input.selectionStart, input.selectionEnd, "end");
    else if (caret && input.selectionStart > 0) input.setRangeText("", input.selectionStart - 1, input.selectionStart, "end");
    else if (!caret) input.value = input.value.slice(0, -1);
  } else if (caret) {
    input.setRangeText(character, input.selectionStart, input.selectionEnd, "end");
  } else {
    input.value += character;
  }
  if (oskShift && key !== "backspace") setShift(false);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

const RIPPLE_TARGETS = ".button, .icon-button, .menu-button, .menu-tab, .live-card, .place-card, .toggle, .osk-key, .osk-close";

function ripple(event) {
  const target = event.target.closest(RIPPLE_TARGETS);
  if (!target || target.disabled || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const rect = target.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 2;
  const wave = document.createElement("span");
  wave.className = "ripple";
  wave.style.width = `${size}px`;
  wave.style.height = `${size}px`;
  wave.style.left = `${event.clientX - rect.left - size / 2}px`;
  wave.style.top = `${event.clientY - rect.top - size / 2}px`;
  wave.addEventListener("animationend", () => wave.remove());
  target.append(wave);
}

function requestSettingsClose() {
  if (dirty && !window.confirm("Ungespeicherte Änderungen verwerfen?")) return;
  dirty = false;
  closeDialog(elements.settings);
}

elements.live.addEventListener("load", () => {
  if (!elements.live.getAttribute("src") || elements.live.src === "about:blank") return;
  setStreamView({ state: "loaded", full: "Stream-Seite geladen · Wiedergabe nicht verifizierbar", card: null });
});
elements.live.addEventListener("error", () => {
  setStreamView({
    state: "error",
    full: "Stream-Einbettung möglicherweise blockiert",
    card: { title: "Stream nicht erreichbar", text: "Die Stream-Seite meldet einen Fehler. Die Einbettung ist möglicherweise blockiert." },
  });
});
byId("streamReload").addEventListener("click", () => {
  if (runtimeConfig?.stream) configureStream(runtimeConfig.stream, true);
  refreshState();
});
byId("reloadStreamPanel").addEventListener("click", () => configureStream(collectConfig().stream, true));

elements.hotspot.addEventListener("click", () => beginAdmin(elements.hotspot));
document.querySelectorAll(".menu-tab").forEach((tab) => tab.addEventListener("click", () => showTab(tab.dataset.tab)));
byId("liveSearchBtn").addEventListener("click", () => { hideKeyboard(); searchLive(elements.liveQuery.value.trim()); });
byId("placeSearchBtn").addEventListener("click", searchPlaces);
elements.liveQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); byId("liveSearchBtn").click(); }
});
elements.placeQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter") { event.preventDefault(); searchPlaces(); }
});
// Fokuswechsel verhindern, damit das Eingabefeld Fokus und Cursor behält; getippt wird beim Loslassen (click).
elements.osk.addEventListener("pointerdown", (event) => event.preventDefault());
elements.osk.addEventListener("mousedown", (event) => event.preventDefault());
elements.osk.addEventListener("click", (event) => {
  const button = event.target.closest("[data-key]");
  if (button) typeKey(button.dataset.key);
});
document.addEventListener("pointerdown", ripple);
document.addEventListener("focusin", (event) => {
  const input = event.target;
  if (input instanceof HTMLInputElement && ["text", "search", "password", "number"].includes(input.type) && input.closest("dialog")) showKeyboard(input);
  else if (input instanceof HTMLTextAreaElement && input.closest("dialog")) showKeyboard(input);
});
elements.settings.addEventListener("close", hideKeyboard);
elements.pinDialog.addEventListener("close", hideKeyboard);
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
