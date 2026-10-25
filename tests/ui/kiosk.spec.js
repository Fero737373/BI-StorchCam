const zlib = require("node:zlib");
const { test, expect } = require("@playwright/test");

const baseConfig = {
  app: { name: "BI-StorchCam", language: "de", timezone: "Europe/Berlin", cache_dir: "~/.cache/BI-StorchCam", config_schema_version: 4 },
  server: { host: "127.0.0.1", port: 8000, max_request_bytes: 262144, admin_session_minutes: 30 },
  kiosk: { enabled: true, browser: "auto", profile_dir: "", disable_screensaver: true, use_gpu: true, browser_restart_seconds: 3, browser_restart_max_seconds: 60, browser_stable_seconds: 30, browser_max_failures: 8, log_file: "~/.cache/BI-StorchCam/chromium.log", log_max_bytes: 2097152, log_backups: 3, extra_flags: [] },
  screen: { hardware_profile: "generic", output: "auto", rotation: "none", touch_device: "", touch_matrix: "" },
  location: { label: "Bielefeld Innenstadt mit einem bewusst sehr langen Standortnamen", latitude: 52.0302, longitude: 8.5325 },
  stream: { url: "http://127.0.0.1:4173/mock-stream", muted: true, autoplay: true },
  admin: { pin_hash: "", require_pin: true },
  youtube: { api_key: "", default_query: "Storch" },
  ui: { theme: "dark", layout_profile: "auto", clock: { enabled: true }, weather: { enabled: true }, transit: { enabled: true }, system: { enabled: true } },
  weather: { provider: "openmeteo", refresh_seconds: 300, forecast_hours: 8, rain_mm_threshold: 0.1, rain_probability_threshold: 45 },
  transit: { provider: "vrr", refresh_seconds: 60, default_max_rows: 2, target_len: 16, stops: [] },
  logging: { level: "INFO", max_bytes: 2097152, backups: 3 },
};

// Gleiche Richtlinie wie server.py, damit CSP-Verstöße auch unter dem statischen Testserver auffallen.
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; "
  + "img-src 'self' data: https://i.ytimg.com; "
  + "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com http://127.0.0.1:4173; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";

const PROBABILITIES = [10, 20, 60, 75, 40, 15, 5, 5];

function forecast() {
  return PROBABILITIES.map((probability, index) => ({
    time: `2026-07-21T${String(14 + index).padStart(2, "0")}:00:00+02:00`,
    rain_mm: probability >= 45 ? 0.6 : 0,
    probability,
    code: probability >= 45 ? 61 : 2,
    rainy: probability >= 45,
  }));
}

function stateFor(config, overrides = {}) {
  return {
    generated_at: "2026-07-21T20:00:00+00:00",
    config: { ui: config.ui, screen: config.screen, stream: config.stream, location: config.location, timezone: config.app.timezone, transit_provider: "vrr", transit_stop_count: 2 },
    weather: {
      ok: true,
      text: "Bielefeld · teils bewölkt · 21 °C · Regen ab 16:00 (60 %)",
      condition: "teils bewölkt",
      code: 2,
      temp: 21,
      feels: 19,
      wind: 14,
      hum: 78,
      rain: 0,
      forecast: forecast(),
      updated_at: "2026-07-21T21:55:00+02:00",
      stale: false,
    },
    boards: [
      { title: "Schneiderstraße", ok: true, checked_at: "2026-07-21T19:59:00+00:00", rows: [{ line: "31", target: "Schildesche", mins: "3 min", minutes: 3 }, { line: "31", target: "Universität", mins: "11 min", minutes: 11 }] },
      { title: "Altdorfer Straße", ok: true, checked_at: "2026-07-21T19:59:00+00:00", rows: [{ line: "26", target: "Jahnplatz", mins: "7 min", minutes: 7 }] },
    ],
    system: { cpu: null, ram: 42, temp: null, uptime: "2h 3m" },
    ...overrides,
  };
}

function png(width, height, pixel) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (width * 4 + 1)] = 0;
    for (let x = 0; x < width; x += 1) {
      const [r, g, b, a] = pixel(x, y);
      raw.set([r, g, b, a], y * (width * 4 + 1) + 1 + x * 4);
    }
  }
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buffer) => {
    let c = 0xffffffff;
    for (const byte of buffer) c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const length = Buffer.alloc(4);
    length.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type), data]);
    const sum = Buffer.alloc(4);
    sum.writeUInt32BE(crc(body));
    return Buffer.concat([length, body, sum]);
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 6, 0, 0, 0], 8);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", header),
    chunk("IDAT", zlib.deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const THUMBNAIL = png(320, 180, (x, y) => ((x + y) % 64 < 3 || (x * 3 + y) % 97 < 2 ? [92, 108, 104, 255] : [52, 66, 62, 255]));
const LIVE_RESULTS = [
  { video_id: "rurvbn9yH-k", title: "Live aus dem Storchennest in Leutershausen", channel: "Heimatverein Leutershausen", thumbnail: "https://i.ytimg.com/vi/rurvbn9yH-k/hq720.jpg", embed_url: "https://www.youtube.com/embed/rurvbn9yH-k" },
  { video_id: "W2CicgFq5oo", title: "Live Storchennest Kirchzarten", channel: "regiowebcam", thumbnail: "https://i.ytimg.com/vi/W2CicgFq5oo/hq720.jpg", embed_url: "https://www.youtube.com/embed/W2CicgFq5oo" },
];

async function mockBackend(page, config = structuredClone(baseConfig), overrides = {}, { open = false } = {}) {
  let savedConfig = config;
  const cspErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error" && /Content Security Policy/i.test(message.text())) cspErrors.push(message.text());
  });
  await page.route("http://127.0.0.1:4173/**", async (route) => {
    const request = route.request();
    if (request.resourceType() !== "document" || request.frame() !== page.mainFrame()) return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": CSP, "x-content-type-options": "nosniff" } });
  });
  await page.route("**/api/state", (route) => route.fulfill({ json: stateFor(savedConfig, overrides) }));
  await page.route("**/api/admin/status", (route) => route.fulfill({ json: open
    ? { ok: true, pin_required: false, pin_configured: true, authenticated: true }
    : { ok: true, pin_required: true, pin_configured: false, authenticated: false } }));
  await page.route("**/api/live/search?*", (route) => route.fulfill({ json: { query: "Storch", results: LIVE_RESULTS } }));
  await page.route("**/api/location/search?*", (route) => route.fulfill({ json: { query: "Tokio", results: [{ name: "Tokio", region: "Japan", latitude: 35.6895, longitude: 139.6917, timezone: "Asia/Tokyo" }] } }));
  await page.route("https://i.ytimg.com/**", (route) => route.fulfill({ contentType: "image/png", body: THUMBNAIL }));
  await page.route("**/api/admin/setup", (route) => route.fulfill({ json: { ok: true, token: "test-token", expires_in: 1800 } }));
  await page.route("**/api/admin/login", (route) => route.fulfill({ json: { ok: true, token: "test-token", expires_in: 1800 } }));
  await page.route("**/api/config", (route) => route.fulfill({ json: { path: "/tmp/config.json", config: savedConfig } }));
  await page.route("**/api/config/save", async (route) => {
    const request = route.request().postDataJSON();
    savedConfig = request.config;
    await route.fulfill({ json: { ok: true, path: "/tmp/config.json", config: savedConfig } });
  });
  await page.route("**/api/station/search?*", (route) => route.fulfill({ json: { query: "Jahnplatz", results: [{ station_id: "23000001", station_name: "Bielefeld Jahnplatz" }] } }));
  await page.route("**/mock-stream?*", (route) => route.fulfill({
    contentType: "text/html",
    body: "<title>Mock stream</title><body style=\"margin:0;height:100vh;background:linear-gradient(180deg,#24343b,#121c20 55%,#1d2a24)\"></body>",
  }));
  return { getSaved: () => savedConfig, cspErrors };
}

function overlaps(a, b) {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

for (const viewport of [
  { width: 1024, height: 600, expected: "minimal", hours: 6 },
  { width: 1280, height: 720, expected: "standard", hours: 8 },
  { width: 1920, height: 1080, expected: "information", hours: 8 },
]) {
  test(`info bar layout at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const { cspErrors } = await mockBackend(page);
    await page.goto("/");
    await expect(page.locator("body")).toHaveAttribute("data-layout", viewport.expected);
    const stage = await page.locator("#stage").boundingBox();
    expect(stage.width).toBe(viewport.width);
    expect(stage.height).toBe(viewport.height);
    await expect(page.locator("#clock")).toBeVisible();
    await expect(page.locator("#weatherText")).toContainText("21 °C");

    const bar = await page.locator("#infobar").boundingBox();
    expect(bar.x).toBeGreaterThanOrEqual(0);
    expect(bar.y).toBeGreaterThanOrEqual(0);
    expect(bar.x + bar.width).toBeLessThanOrEqual(viewport.width);
    expect(bar.y + bar.height).toBeLessThanOrEqual(viewport.height);
    // Oben rechts gibt es keinen sichtbaren Status mehr; der Satz bleibt nur für Screenreader.
    expect(await page.locator("#streamStatus").evaluate((node) => node.classList.contains("sr-only"))).toBe(true);
    await expect(page.locator("#radar")).toHaveCount(0);

    for (const block of ["#clockbar", "#weather", "#transitPanel"]) {
      const box = await page.locator(block).boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(bar.x);
      expect(box.x + box.width).toBeLessThanOrEqual(bar.x + bar.width + 0.5);
    }

    await expect(page.locator("#transitPanel")).toBeVisible();
    await expect(page.locator(".departure-target")).toHaveText(["Schildesche", "Jahnplatz", "Universität"]);
    await expect(page.locator(".departure-sub").first()).toHaveText("ab Schneiderstraße");

    await expect(page.locator(".rain-col")).toHaveCount(viewport.hours);
    const rainFlags = await page.locator(".rain-col").evaluateAll((columns) => columns.map((column) => column.classList.contains("is-rain")));
    expect(rainFlags).toEqual(PROBABILITIES.slice(0, viewport.hours).map((value) => value >= 45));
    await expect(page.locator("#rainSummary")).toContainText("ab 16 Uhr · 60 %");


    await page.waitForFunction(() => document.fonts.check("600 16px Barlow"));
    expect(await page.evaluate(() => document.fonts.check("600 16px Barlow"))).toBe(true);
    expect(cspErrors).toEqual([]);
  });
}

test("admin PIN setup, station add and save without stream reload", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved } = await mockBackend(page);
  let iframeNavigations = 0;
  page.on("framenavigated", (frame) => { if (frame !== page.mainFrame()) iframeNavigations += 1; });
  await page.goto("/");
  await page.keyboard.press("Control+Alt+S");
  await expect(page.locator("#pinDialog")).toBeVisible();
  await page.locator("#adminPin").fill("1234");
  await page.locator("#adminPinConfirm").fill("1234");
  await page.locator("#submitPin").click();
  await expect(page.locator("#settingsDialog")).toBeVisible();
  await page.getByRole("tab", { name: "ÖPNV" }).click();
  await page.locator("#stationQuery").fill("Jahnplatz");
  await page.locator("#stationSearchBtn").click();
  await page.getByRole("button", { name: "Hinzufügen" }).click();
  await expect(page.locator(".stop-card")).toHaveCount(1);
  await page.getByRole("tab", { name: "Anzeige" }).click();
  await page.locator("#cfgTheme").selectOption("high-contrast");
  const beforeSave = iframeNavigations;
  await page.locator("#saveConfig").click();
  await expect(page.locator("#saveState")).toContainText("Gespeichert");
  expect(iframeNavigations).toBe(beforeSave);
  expect(getSaved().transit.stops).toHaveLength(1);
  expect(getSaved().stream.url).toBe(baseConfig.stream.url);
});

test("explicit profiles and offline states remain readable", async ({ page }) => {
  const config = structuredClone(baseConfig);
  config.ui.layout_profile = "minimal";
  await mockBackend(page, config);
  await page.goto("/");
  await expect(page.locator("body")).toHaveAttribute("data-layout", "minimal");
  await expect(page.locator("#sys")).toContainText("CPU –");
  await expect(page.locator("#streamStatusText")).toContainText("Wiedergabe nicht verifizierbar");
});

test("board error and stale weather show honest states", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { cspErrors } = await mockBackend(page, structuredClone(baseConfig), {
    boards: [
      { title: "Schneiderstraße", ok: true, checked_at: "2026-07-21T19:59:00+00:00", rows: [{ line: "31", target: "Schildesche", mins: "1h 05", minutes: 65 }, { line: "N2", target: "Babenhausen", mins: "jetzt", minutes: 0 }] },
      { title: "Altdorfer Straße", ok: false, checked_at: "2026-07-21T19:58:00+00:00", rows: [], error: "VRR offline" },
    ],
    weather: { ...stateFor(baseConfig).weather, stale: true, error: "offline" },
  });
  await page.goto("/");
  await expect(page.locator(".departure.is-error")).toContainText("Altdorfer Straße: VRR antwortet nicht");
  await expect(page.locator(".departure.is-error")).toContainText("letzte Abfrage 21:58 · neuer Versuch läuft");
  await expect(page.locator(".departure-now")).toHaveText("jetzt");
  await expect(page.locator(".departure").nth(2)).toContainText("1h 05");
  await expect(page.locator("#rainSummary")).toHaveText("Stand 21:55 · offline");
  expect(cspErrors).toEqual([]);
});

test("missing stream and unavailable weather keep the info bar working", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const config = structuredClone(baseConfig);
  config.stream.url = "";
  await mockBackend(page, config, { weather: { ok: false, text: "Bielefeld · Wetter offline", error: "Open-Meteo nicht erreichbar", stale: false } });
  await page.goto("/");
  await expect(page.locator("#streamEmpty")).toBeVisible();
  await expect(page.locator("#streamEmptyTitle")).toHaveText("Kein Livestream konfiguriert");
  await expect(page.locator("#streamReload")).toHaveText("Jetzt neu laden");
  await expect(page.locator("#infobar")).toBeVisible();
  await expect(page.locator("#weather")).toContainText("Wetter nicht verfügbar");
  await expect(page.locator("#weather")).toContainText("Open-Meteo nicht erreichbar");
  const card = await page.locator(".empty-card").boundingBox();
  const bar = await page.locator("#infobar").boundingBox();
  expect(overlaps(card, bar)).toBe(false);
});

test("disabled blocks and narrow screens reflow the info bar", async ({ page }) => {
  const config = structuredClone(baseConfig);
  config.ui.weather.enabled = false;
  config.ui.system.enabled = false;
  await page.setViewportSize({ width: 1280, height: 720 });
  await mockBackend(page, config);
  await page.goto("/");
  await expect(page.locator("#weather")).toBeHidden();
  await expect(page.locator("#sysbar")).toBeHidden();
  await expect(page.locator(".ib-sep:visible")).toHaveCount(1);
  const columns = await page.locator("#infobar").evaluate((bar) => getComputedStyle(bar).gridTemplateColumns.split(" ").length);
  expect(columns).toBe(3);

  await page.setViewportSize({ width: 740, height: 480 });
  config.ui.weather.enabled = true;
  config.ui.system.enabled = true;
  await page.reload();
  await expect(page.locator("#sysbar")).toBeHidden();
  await expect(page.locator(".departure")).toHaveCount(2);
});

test("no stops configured shows setup hint", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const config = structuredClone(baseConfig);
  await mockBackend(page, config, { boards: [], config: { ...stateFor(config).config, transit_stop_count: 0 } });
  await page.goto("/");
  await expect(page.locator("#boards")).toContainText("Keine Haltestellen eingerichtet");
  await expect(page.locator("#boards")).toContainText("Im Adminmodus hinzufügen");
});

test.describe("reference screenshots", () => {
  test.skip(!process.env.SCREENSHOT_DIR, "Nur mit SCREENSHOT_DIR, z. B. für README-Referenzbilder");

  const errorState = {
    boards: [
      { title: "Schneiderstraße", ok: true, checked_at: "2026-07-21T19:59:00+00:00", rows: [{ line: "31", target: "Schildesche", mins: "jetzt", minutes: 0 }, { line: "N2", target: "Babenhausen", mins: "1h 05", minutes: 65 }] },
      { title: "Altdorfer Straße", ok: false, checked_at: "2026-07-21T19:58:00+00:00", rows: [], error: "VRR offline" },
    ],
  };
  const shots = [
    { name: "standard-1280x720", width: 1280, height: 720 },
    { name: "minimal-1024x600", width: 1024, height: 600 },
    { name: "information-1920x1080", width: 1920, height: 1080 },
    { name: "minimal-800x480", width: 800, height: 480 },
    { name: "light-1280x720", width: 1280, height: 720, theme: "light" },
    { name: "contrast-1280x720", width: 1280, height: 720, theme: "high-contrast" },
    { name: "errors-1280x720", width: 1280, height: 720, overrides: errorState },
    { name: "nostream-1280x720", width: 1280, height: 720, noStream: true },
    { name: "menu-live-1280x720", width: 1280, height: 720, menu: "live" },
    { name: "menu-place-1280x720", width: 1280, height: 720, menu: "place" },
  ];
  for (const shot of shots) {
    test(shot.name, async ({ page }) => {
      const config = structuredClone(baseConfig);
      if (shot.theme) config.ui.theme = shot.theme;
      if (shot.noStream) config.stream.url = "";
      await page.setViewportSize({ width: shot.width, height: shot.height });
      const { cspErrors } = await mockBackend(page, config, shot.overrides || {}, { open: !!shot.menu });
      await page.goto("/");
      await page.waitForFunction(() => document.fonts.check("600 16px Barlow"));
      await expect(page.locator(".departure, .board-message").first()).toBeVisible();
      if (shot.menu) {
        await page.getByRole("button", { name: "Menü öffnen" }).click();
        await expect(page.locator(".live-card").first()).toBeVisible();
      }
      if (shot.menu === "place") {
        await page.getByRole("tab", { name: "Ort" }).click();
        await page.locator("#placeQuery").click();
        for (const key of ["t", "o", "k", "i", "o"]) await page.locator(`#osk [data-key="${key}"]`).click();
        await page.locator("#placeSearchBtn").click();
        await page.locator("#placeQuery").click();
      }
      await page.waitForTimeout(400);
      await page.screenshot({ path: `${process.env.SCREENSHOT_DIR}/${shot.name}.png` });
      const metrics = await page.evaluate(() => {
        const box = (selector) => { const r = document.querySelector(selector)?.getBoundingClientRect(); return r ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] : null; };
        const font = (selector) => { const c = document.querySelector(selector) && getComputedStyle(document.querySelector(selector)); return c ? `${c.fontSize}/${c.fontWeight}` : null; };
        return {
          infobar: box("#infobar"), columns: getComputedStyle(document.querySelector("#infobar")).gridTemplateColumns,
          row: box(".departure"), badge: box(".departure-line"),
          clock: font("#clock"), date: font("#date"), sys: font("#sys"), temp: font("#weatherTemp"), condition: font("#weatherCondition"),
          details: font("#weatherDetails"), track: box(".rain-track"), target: font(".departure-target"), num: font(".departure-num"),
        };
      });
      require("node:fs").writeFileSync(`${process.env.SCREENSHOT_DIR}/${shot.name}.json`, JSON.stringify(metrics));
      if (shot.name.startsWith("standard")) {
        await page.evaluate(() => { const image = new Image(); image.src = "https://example.com/csp-probe.png"; document.body.append(image); });
        await expect.poll(() => cspErrors.length).toBeGreaterThan(0);
      }
    });
  }
});

test("menu button opens the menu without PIN; live stream and place are chosen by tapping", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { getSaved, cspErrors } = await mockBackend(page, structuredClone(baseConfig), {}, { open: true });
  await page.goto("/");
  await page.getByRole("button", { name: "Menü öffnen" }).click();
  await expect(page.locator("#settingsDialog")).toBeVisible();
  await expect(page.locator("#pinDialog")).toBeHidden();
  await expect(page.locator(".live-card")).toHaveCount(2);
  await expect(page.locator("#liveQuery")).toHaveValue("Storch");
  await page.locator(".live-card").nth(1).click();
  await expect(page.locator("#settingsDialog")).toBeHidden();
  expect(getSaved().stream.url).toBe("https://www.youtube.com/embed/W2CicgFq5oo");

  await page.getByRole("button", { name: "Menü öffnen" }).click();
  await page.getByRole("tab", { name: "Ort" }).click();
  await page.locator("#placeQuery").click();
  await expect(page.locator("#osk")).toBeVisible();
  for (const key of ["t", "o", "k", "i", "o"]) await page.locator(`#osk [data-key="${key}"]`).click();
  await expect(page.locator("#placeQuery")).toHaveValue("Tokio");
  await expect(page.locator("#placeQuery")).toBeFocused();
  await page.locator('#osk [data-key="enter"]').click();
  await page.locator(".place-card").first().click();
  await expect(page.locator("#placeStatus")).toContainText("Ort übernommen: Tokio");
  const saved = getSaved();
  expect([saved.location.label, saved.location.latitude, saved.location.longitude, saved.app.timezone]).toEqual(["Tokio", 35.6895, 139.6917, "Asia/Tokyo"]);
  expect(cspErrors).toEqual([]);
});
