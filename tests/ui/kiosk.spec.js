const { test, expect } = require("@playwright/test");

// Konfiguration in der Form, die /api/config liefert (Schema 5).
const baseConfig = {
  app: { name: "BI-StorchCam", language: "de", timezone: "Europe/Berlin", cache_dir: "~/.cache/BI-StorchCam", config_schema_version: 5 },
  server: { host: "127.0.0.1", port: 8000, max_request_bytes: 262144, admin_session_minutes: 30, public_url: "", lan_access: false },
  kiosk: { enabled: true, browser: "auto", profile_dir: "", disable_screensaver: true, use_gpu: true, browser_restart_seconds: 3, browser_restart_max_seconds: 60, browser_stable_seconds: 30, browser_max_failures: 8, log_file: "~/.cache/BI-StorchCam/chromium.log", log_max_bytes: 2097152, log_backups: 3, extra_flags: [] },
  screen: { hardware_profile: "generic", output: "auto", rotation: "none", touch_device: "", touch_matrix: "" },
  location: { label: "Bielefeld", latitude: 52.0302, longitude: 8.5325 },
  stream: { url: "http://127.0.0.1:4173/mock-stream", muted: true, autoplay: true, quality: "auto", max_fps: 30, audio: "off", favorites: [], auto_fallback: true, notes: {} },
  admin: { pin_hash: "", require_pin: true },
  youtube: { api_key: "", default_query: "Storch" },
  music: { source: "off", spotify: { client_id: "" }, radio: { favorites: [] } },
  ui: {
    theme: "dark", sky: "auto", layout_profile: "auto", distance: 2, compact_after: 120, setup_done: true,
    night: { enabled: false, start: "23:00", end: "06:00", screen_off: false },
    clock: { enabled: true }, weather: { enabled: true }, transit: { enabled: true }, system: { enabled: true },
  },
  weather: { provider: "openmeteo", refresh_seconds: 300, forecast_hours: 8, rain_mm_threshold: 0.1, rain_probability_threshold: 45, warnings: "moderate" },
  transit: {
    provider: "vrr", refresh_seconds: 60, default_max_rows: 2, target_len: 16, leave_mode: true,
    stops: [{ title: "", station_name: "Bielefeld, Schneiderstraße", station_id: "23000001", line_filter: [], nightbus_only: false, hide_if_empty: true, max_rows: 3, walk_minutes: 5 }],
  },
  logging: { level: "INFO", max_bytes: 2097152, backups: 3 },
};

// Gleiche Richtlinie wie server.py, damit CSP-Verstöße auch unter dem statischen Testserver auffallen.
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; "
  + "img-src 'self' data: https://i.ytimg.com https://i.scdn.co https://*.googleusercontent.com https://yt3.ggpht.com; "
  + "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com http://127.0.0.1:4173; media-src 'self' blob:; worker-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";

const RAIN = [10, 20, 60, 75, 40, 15, 5, 5, 10, 20, 30, 20, 10, 5, 5, 10, 15, 20, 25, 20, 15, 10, 5, 5, 5];

function weather(stale = false) {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  const hourly = RAIN.map((probability, index) => {
    const at = new Date(start.getTime() + index * 3600e3);
    return { time: at.toISOString(), hour: at.getHours(), temp: 18 + Math.round(3 * Math.cos(index / 4)), probability, rain_mm: probability >= 45 ? 0.6 : 0, wind: 12 + (index % 4), code: probability >= 45 ? 61 : 2, is_day: at.getHours() >= 7 && at.getHours() < 19 };
  });
  const day = new Date();
  const sun = [0, 1].map((offset) => ({
    rise: new Date(day.getFullYear(), day.getMonth(), day.getDate() + offset, 6, 40).toISOString(),
    set: new Date(day.getFullYear(), day.getMonth(), day.getDate() + offset, 18, 20).toISOString(),
  }));
  return { ok: true, label: "Bielefeld", text: "", condition: "teils bewölkt", code: 2, is_day: true, temp: 21, feels: 19, wind: 14, hum: 78, rain: 0, forecast: [], hourly, sun, rain_threshold: 45, updated_at: new Date().toISOString(), stale };
}

function departure(line, type, target, minutes, delay = 0) {
  const now = Math.floor(Date.now() / 1000);
  return { line, type, target, mins: `${minutes} min`, minutes, delay, realtime: true, planned: now + (minutes - delay) * 60, at: now + minutes * 60, platform: "" };
}

function boards() {
  return [{
    title: "Schneiderstraße", station_id: "23000001", station_name: "Bielefeld, Schneiderstraße", ok: true, walk_minutes: 5, hide_if_empty: true,
    checked_at: new Date().toISOString(),
    rows: [departure("31", "bus", "Schildesche", 6, 2), departure("4", "tram", "Lohmannshof", 14), departure("N2", "night", "Babenhausen", 75)],
    lines: [{ line: "4", type: "tram" }, { line: "31", type: "bus" }, { line: "N2", type: "night" }],
  }];
}

function stateFor(config, overrides = {}) {
  return {
    generated_at: new Date().toISOString(),
    config: {
      ui: config.ui, screen: config.screen, stream: config.stream, location: config.location, timezone: config.app.timezone,
      transit_provider: "vrr", transit_stop_count: config.transit.stops.length, transit_leave_mode: config.transit.leave_mode,
      music_source: config.music.source, warnings: config.weather.warnings,
    },
    weather: weather(),
    boards: boards(),
    system: { cpu: 12, ram: 42, temp: 51, uptime: "2h 3m" },
    music: { enabled: false },
    warnings: { ok: true, enabled: true, covered: true, alerts: [] },
    health: {},
    ...overrides,
  };
}

const LIVE_RESULTS = [
  { video_id: "rurvbn9yH-k", title: "Live aus dem Storchennest in Leutershausen", channel: "Heimatverein Leutershausen", thumbnail: "", embed_url: "https://www.youtube.com/embed/rurvbn9yH-k" },
  { video_id: "W2CicgFq5oo", title: "Live Storchennest Kirchzarten", channel: "regiowebcam", thumbnail: "", embed_url: "https://www.youtube.com/embed/W2CicgFq5oo" },
];
const STATIONS = [
  { uuid: "11111111-aaaa", name: "WDR 2", url: "http://radio.example.org/wdr2.mp3", country: "Germany", state: "", codec: "MP3", bitrate: 128, tags: ["pop", "news"], votes: 900 },
  { uuid: "22222222-bbbb", name: "Deutschlandfunk", url: "http://radio.example.org/dlf.mp3", country: "Germany", state: "", codec: "MP3", bitrate: 128, tags: ["news"], votes: 800 },
];

async function mockBackend(page, { config = structuredClone(baseConfig), overrides = {}, open = true } = {}) {
  let savedConfig = config;
  let state = overrides;
  const cspErrors = [];
  const pageErrors = [];
  const calls = [];
  page.on("console", (message) => {
    if (message.type() === "error" && /Content Security Policy/i.test(message.text())) cspErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  await page.route("http://127.0.0.1:4173/**", async (route) => {
    const request = route.request();
    if (request.resourceType() !== "document" || request.frame() !== page.mainFrame()) return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": CSP, "x-content-type-options": "nosniff" } });
  });
  const json = (pattern, body) => page.route(pattern, (route) => {
    calls.push([route.request().url(), route.request().postDataJSON?.() ?? null]);
    return route.fulfill({ json: typeof body === "function" ? body(route.request()) : body });
  });
  await json("**/api/state", () => stateFor(savedConfig, state));
  await json("**/api/admin/status", () => (open
    ? { ok: true, pin_required: false, pin_configured: true, authenticated: true, remote: false, pin_login: true }
    : { ok: true, pin_required: true, pin_configured: false, authenticated: false, remote: false, pin_login: true }));
  await json("**/api/stream/source*", { kind: "embed", reason: "Test" });
  await json("**/api/live/search?*", { query: "Storch", results: LIVE_RESULTS });
  await json("**/api/location/search?*", { query: "Tokio", results: [{ name: "Tokio", region: "Japan", latitude: 35.6895, longitude: 139.6917, timezone: "Asia/Tokyo" }] });
  await json("**/api/station/search?*", { query: "Jahnplatz", results: [{ station_id: "23000002", station_name: "Bielefeld Jahnplatz" }] });
  await json("**/api/admin/setup", { ok: true, token: "test-token", expires_in: 1800 });
  await json("**/api/admin/login", { ok: true, token: "test-token", expires_in: 1800 });
  await json("**/api/config", () => ({ path: "/tmp/config.json", config: savedConfig, youtube_key_set: false, spotify_connected: false, ytmusic_connected: false }));
  await json("**/api/config/save", (request) => {
    savedConfig = request.postDataJSON().config;
    return { ok: true, path: "/tmp/config.json", config: savedConfig };
  });
  await json("**/api/radio/search", { ok: true, results: STATIONS });
  await json("**/api/radio/play", (request) => ({ ok: true, station: request.postDataJSON().station }));
  await json("**/api/music/recent", { ok: true, results: [] });
  await json("**/api/system/info", { ok: true, version: "test", uptime_seconds: 60, config_saved: "", backlight: false, public_url: "", remote: false });
  await json("**/api/pair/**", { ok: true, active: true, code: "123456", expires_in: 600, url: "", claimed: false });
  await json("**/api/bluetooth", { ok: true, available: false, error: "Bluetooth nicht verfügbar", devices: [] });
  await json("**/api/music/**", { ok: true, status: "idle", connected: false, paired: false });
  await json("**/api/display/power", { ok: true, switched: false });
  await page.route("**/mock-stream?*", (route) => route.fulfill({
    contentType: "text/html",
    body: "<title>Mock stream</title><body style=\"margin:0;height:100vh;background:linear-gradient(180deg,#24343b,#121c20 55%,#1d2a24)\"></body>",
  }));
  return { getSaved: () => savedConfig, setState: (value) => { state = value; }, cspErrors, pageErrors, calls };
}

function inside(box, viewport) {
  return box.x >= -1 && box.y >= -1 && box.x + box.width <= viewport.width + 1 && box.y + box.height <= viewport.height + 1;
}

function overlaps(a, b) {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

async function openMenu(page) {
  await page.getByRole("button", { name: "Menü öffnen" }).click();
  await expect(page.locator("#sheet")).toBeVisible();
}

for (const viewport of [{ width: 800, height: 480 }, { width: 1024, height: 600 }, { width: 1280, height: 720 }, { width: 1920, height: 1080 }, { width: 720, height: 1280 }]) {
  test(`info bar at ${viewport.width}x${viewport.height} shows clock, weather strip and leave times`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const { cspErrors, pageErrors } = await mockBackend(page);
    await page.goto("/");
    await expect(page.locator("#clock")).toHaveText(/^\d{2}:\d{2}$/);
    await expect(page.locator("#weatherTemp")).toHaveText("21°");
    await expect.poll(() => page.locator("#strip rect").count()).toBeGreaterThan(10);
    await expect(page.locator("#boards .departure").first()).toBeVisible();
    // Bus in 6 Minuten, 5 Minuten Weg: jetzt losgehen.
    await expect(page.locator("#boards .departure").first()).toContainText("Jetzt los");
    await expect(page.locator("#boards .delay").first()).toHaveText("+2");
    const bar = await page.locator("#infobar").boundingBox();
    expect(inside(bar, viewport)).toBe(true);
    for (const selector of ["#clockBlock", "#weatherBlock", "#transitBlock"]) {
      const box = await page.locator(selector).boundingBox();
      expect(inside(box, viewport), selector).toBe(true);
    }
    const menu = await page.locator("#menuBtn").boundingBox();
    expect(overlaps(menu, bar)).toBe(false);
    expect(cspErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
}

test("plain departure times without leave mode and honest error states", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const config = structuredClone(baseConfig);
  config.transit.leave_mode = false;
  const failing = [{ title: "Altdorfer Straße", station_id: "9", station_name: "Bielefeld, Altdorfer Straße", ok: false, error: "Zeitüberschreitung", rows: [], lines: [], walk_minutes: 0, checked_at: new Date().toISOString() }];
  await mockBackend(page, { config, overrides: { boards: [...boards(), ...failing], weather: weather(true) } });
  await page.goto("/");
  await expect(page.locator("#trTitle")).toHaveText("Abfahrten");
  const first = page.locator("#boards .departure:not(.is-error)").first();
  await expect(first).not.toContainText("Jetzt los");
  await expect(first.locator(".dep-num")).toHaveText(/^[56]$/);
  await expect(page.locator("#boards .departure.is-error")).toContainText("Altdorfer Straße");
  await expect(page.locator("#weatherBlock")).toHaveClass(/is-stale/);
});

test("official DWD warning appears above the bar and opens its details", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const alert = { id: "a", headline: "Amtliche Warnung vor Sturmböen", event: "STURMBÖEN", severity: "moderate", level: 2, onset: new Date().toISOString(), expires: new Date(Date.now() + 3 * 3600e3).toISOString(), description: "Sturmböen um 70 km/h.", instruction: "" };
  await mockBackend(page, { overrides: { warnings: { ok: true, enabled: true, covered: true, alerts: [alert] } } });
  await page.goto("/");
  await expect(page.locator("#warning")).toBeVisible();
  await expect(page.locator("#warningText")).toContainText("Sturmböen");
  await page.locator("#warning").click();
  await expect(page.locator("#detailWarning")).toBeVisible();
  await expect(page.locator("#dwarnBody")).toContainText("70 km/h");
});

test("details for weather and departures open by tapping the bar", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await mockBackend(page);
  await page.goto("/");
  await page.locator("#weatherBlock").click();
  await expect(page.locator("#detailWeather")).toBeVisible();
  await expect.poll(() => page.locator("#wchart polyline").count()).toBeGreaterThan(0);
  await page.locator("#detailWeather [data-close]").click();
  await expect(page.locator("#detailWeather")).toBeHidden();
  await page.locator("#transitBlock").click();
  await expect(page.locator("#detailDepart")).toBeVisible();
  await expect(page.locator("#boardTable tbody tr")).toHaveCount(3);
});

test("menu opens without PIN; a theme applies at once and can be undone", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved, cspErrors } = await mockBackend(page);
  await page.goto("/");
  await openMenu(page);
  await expect(page.locator("#pinDialog")).toBeHidden();
  await page.getByRole("tab", { name: "Anzeige" }).click();
  await page.locator('.theme-card[data-theme="flap"]').click();
  await expect(page.locator("body")).toHaveAttribute("data-theme", "flap");
  expect(getSaved().ui.theme).toBe("flap");
  await expect(page.locator("#toastUndo")).toBeVisible();
  await page.locator("#toastUndo").click();
  await expect(page.locator("body")).toHaveAttribute("data-theme", "dark");
  expect(getSaved().ui.theme).toBe("dark");
  await page.locator('#distSeg [data-dist="3"]').click();
  await expect.poll(() => getSaved().ui.distance).toBe(3);
  expect(cspErrors).toEqual([]);
});

test("first use asks for a new PIN before the menu opens", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await mockBackend(page, { open: false });
  await page.goto("/");
  await page.getByRole("button", { name: "Menü öffnen" }).click();
  await expect(page.locator("#pinDialog")).toBeVisible();
  await expect(page.locator("#pinTitle")).toHaveText("Admin-PIN erstmals festlegen");
  await page.locator("#adminPin").fill("2468");
  await page.locator("#adminPinConfirm").fill("2468");
  await page.locator("#submitPin").click();
  await expect(page.locator("#pinDialog")).toBeHidden();
  await expect(page.locator("#sheet")).toBeVisible();
});

test("live search plays by tapping and the star keeps a favorite", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved } = await mockBackend(page);
  await page.goto("/");
  await openMenu(page);
  await expect(page.locator("#liveResults .result")).toHaveCount(2);
  await page.locator("#liveResults .result").nth(0).locator(".star").click();
  await expect.poll(() => getSaved().stream.favorites.length).toBe(1);
  expect(getSaved().stream.favorites[0].title).toBe("Live aus dem Storchennest in Leutershausen");
  await page.locator("#liveResults .result").nth(1).click();
  await expect.poll(() => getSaved().stream.url).toBe("https://www.youtube.com/embed/W2CicgFq5oo");
  await expect(page.locator("#favList")).toContainText("Leutershausen");
});

test("place search moves clock and weather to the chosen place", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved } = await mockBackend(page);
  await page.goto("/");
  await openMenu(page);
  await page.getByRole("tab", { name: "Ort" }).click();
  await page.locator("#placeQuery").click();
  await expect(page.locator("#osk")).toBeVisible();
  for (const key of ["t", "o", "k", "i", "o"]) await page.locator(`#osk [data-key="${key}"]`).click();
  await expect(page.locator("#placeQuery")).toHaveValue("Tokio");
  await page.locator('#osk [data-key="enter"]').click();
  await page.locator("#placeResults .pick").first().click();
  await expect.poll(() => getSaved().location.label).toBe("Tokio");
  const saved = getSaved();
  expect([saved.location.latitude, saved.location.longitude, saved.app.timezone]).toEqual([35.6895, 139.6917, "Asia/Tokyo"]);
});

test("stops are added from the search and the walk time is saved", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved } = await mockBackend(page);
  await page.goto("/");
  await openMenu(page);
  await page.getByRole("tab", { name: "ÖPNV" }).click();
  await page.locator("#stopQuery").fill("Jahnplatz");
  await page.locator("#stopSearchBtn").click();
  await page.locator("#stopResults .pick").first().click();
  await expect.poll(() => getSaved().transit.stops.length).toBe(2);
  expect(getSaved().transit.stops[1].station_id).toBe("23000002");
  await page.locator("#stopCards .card").first().getByRole("button", { name: "Eine Minute mehr" }).click();
  await expect.poll(() => getSaved().transit.stops[0].walk_minutes).toBe(6);
});

test("radio search plays a station and the star keeps it as favourite", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved, calls } = await mockBackend(page);
  await page.goto("/");
  await openMenu(page);
  await page.getByRole("tab", { name: "Musik" }).click();
  await expect(page.locator("#mResults .mrow")).toHaveCount(2);
  await page.locator("#mResults .mrow").first().click();
  await expect.poll(() => calls.filter(([url]) => url.endsWith("/api/radio/play")).length).toBe(1);
  expect(calls.find(([url]) => url.endsWith("/api/radio/play"))[1].station.uuid).toBe("11111111-aaaa");
  await page.locator("#mResults .mrow").nth(1).locator(".fav").click();
  await expect.poll(() => getSaved().music.radio.favorites.length).toBe(1);
  expect(getSaved().music.radio.favorites[0].name).toBe("Deutschlandfunk");
});

test("radio now playing card shows the station and the current song", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const music = { enabled: true, ok: true, playing: true, controls: "pi", source: "radio", device: "pi", title: "WDR 2", artist: "Coldplay – Viva la Vida", cover: "", station: STATIONS[0], live: true, progress_ms: 0, duration_ms: 0, paused: false, volume: 60, fetched_at: Date.now(), sleep_end: 0 };
  await mockBackend(page, { overrides: { music } });
  await page.goto("/");
  await expect(page.locator("#nowPlaying")).toBeVisible();
  await expect(page.locator("#npTitle")).toHaveText("WDR 2");
  await expect(page.locator("#npSub")).toContainText("Coldplay");
  await expect(page.locator("#nowPlaying")).toHaveClass(/is-radio/);
});

test("the info bar shrinks to the compact bar and comes back", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await mockBackend(page);
  await page.goto("/");
  await expect(page.locator("#infobar")).toBeVisible();
  await page.locator("#barHandle").click();
  await expect(page.locator("#minibar")).toBeVisible();
  await expect(page.locator("#infobar")).toBeHidden();
  await expect(page.locator("#mbClock")).toHaveText(/\d{2}:\d{2}/);
  await page.locator("#minibar").click();
  await expect(page.locator("#infobar")).toBeVisible();
});

test("first start without a stream opens the setup wizard", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const config = structuredClone(baseConfig);
  config.stream.url = "";
  config.ui.setup_done = false;
  const { getSaved } = await mockBackend(page, { config });
  await page.goto("/");
  await expect(page.locator("#wizard")).toBeVisible();
  await expect(page.locator("#wzTitle")).toContainText("Kamera");
  await page.locator("#wzSkip").click();
  await expect(page.locator("#wizard")).toBeHidden();
  await expect.poll(() => getSaved().ui.setup_done).toBe(true);
});

test("night mode dims the screen and a tap wakes it", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const config = structuredClone(baseConfig);
  config.ui.night = { enabled: true, start: "00:00", end: "23:59", screen_off: false };
  await mockBackend(page, { config });
  await page.goto("/");
  await expect(page.locator("#night")).toBeVisible();
  await expect(page.locator("#nightClock")).toHaveText(/\d{2}:\d{2}/);
  await page.locator("#night").click();
  await expect(page.locator("#night")).toBeHidden();
});

test("YouTube and HLS streams play in the own video player instead of an iframe", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { cspErrors } = await mockBackend(page);
  let playlistRequests = 0;
  await page.route("**/api/stream/source*", (route) => route.fulfill({ json: { kind: "hls", url: "/mock-hls/index.m3u8", title: "Hafen live", channel: "Hafencam", live: true, expires_in: 3600 } }));
  await page.route("**/mock-hls/index.m3u8", (route) => {
    playlistRequests += 1;
    return route.fulfill({ contentType: "application/vnd.apple.mpegurl", body: "#EXTM3U\n#EXT-X-TARGETDURATION:2\n#EXTINF:2.0,\nseg0.ts\n" });
  });
  await page.route("**/mock-hls/seg0.ts", (route) => route.fulfill({ contentType: "video/mp2t", body: Buffer.alloc(188 * 8) }));
  await page.goto("/");
  await expect(page.locator("#player")).toHaveClass(/is-video/);
  await expect(page.locator("#live")).toBeHidden();
  expect(await page.locator("#live").getAttribute("src")).toBeNull();
  await expect.poll(() => playlistRequests).toBeGreaterThan(0);
  // Das Video nimmt keine Berührung an, ein Tippen aufs Bild kann es also nicht anhalten.
  expect(await page.locator("#liveVideo").evaluate((video) => getComputedStyle(video).pointerEvents)).toBe("none");
  await expect(page.locator("#chipTitle")).toHaveText("Hafen live");
  expect(cspErrors).toEqual([]);
});
