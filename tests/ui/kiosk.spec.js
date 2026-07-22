const { test, expect } = require("@playwright/test");

const baseConfig = {
  app: { name: "BI-StorchCam", language: "de", timezone: "Europe/Berlin", cache_dir: "~/.cache/BI-StorchCam", config_schema_version: 4 },
  server: { host: "127.0.0.1", port: 8000, max_request_bytes: 262144, admin_session_minutes: 30 },
  kiosk: { enabled: true, browser: "auto", profile_dir: "", disable_screensaver: true, use_gpu: true, browser_restart_seconds: 3, browser_restart_max_seconds: 60, browser_stable_seconds: 30, browser_max_failures: 8, log_file: "~/.cache/BI-StorchCam/chromium.log", log_max_bytes: 2097152, log_backups: 3, extra_flags: [] },
  screen: { hardware_profile: "generic", output: "auto", rotation: "none", touch_device: "", touch_matrix: "" },
  location: { label: "Bielefeld Innenstadt mit einem bewusst sehr langen Standortnamen", latitude: 52.0302, longitude: 8.5325 },
  stream: { url: "http://127.0.0.1:4173/mock-stream", muted: true, autoplay: true },
  admin: { pin_hash: "" },
  ui: { theme: "dark", layout_profile: "auto", clock: { enabled: true }, weather: { enabled: true }, radar: { enabled: true, width: 280, height: 190, zoom: 10, opacity: 0.92 }, transit: { enabled: true }, system: { enabled: true } },
  weather: { provider: "openmeteo", refresh_seconds: 300, forecast_hours: 8, rain_mm_threshold: 0.1, rain_probability_threshold: 45 },
  transit: { provider: "vrr", refresh_seconds: 60, default_max_rows: 2, target_len: 16, stops: [] },
  radar: { provider: "rainviewer", refresh_seconds: 300 },
  logging: { level: "INFO", max_bytes: 2097152, backups: 3 },
};

function stateFor(config) {
  return {
    generated_at: "2026-07-21T20:00:00+00:00",
    config: { ui: config.ui, screen: config.screen, stream: config.stream, location: config.location, timezone: config.app.timezone, transit_provider: "vrr" },
    weather: { ok: true, text: "Bielefeld · teils bewölkt · 21 °C · kein Regen in den nächsten 8 h" },
    radar: { ok: false, offline: true, label: config.location.label, status: "Radar offline", attribution: "RainViewer · OpenStreetMap-Mitwirkende" },
    boards: [
      { title: "Schneiderstraße", ok: true, rows: [{ line: "31", target: "Schildesche", mins: "3 min" }, { line: "31", target: "Universität", mins: "11 min" }] },
      { title: "Altdorfer Straße", ok: true, rows: [{ line: "26", target: "Jahnplatz", mins: "7 min" }] },
    ],
    system: { cpu: null, ram: 42, temp: null, uptime: "2h 3m" },
  };
}

async function mockBackend(page, config = structuredClone(baseConfig)) {
  let savedConfig = config;
  await page.route("**/api/state", (route) => route.fulfill({ json: stateFor(savedConfig) }));
  await page.route("**/api/admin/status", (route) => route.fulfill({ json: { ok: true, pin_configured: false, authenticated: false } }));
  await page.route("**/api/admin/setup", (route) => route.fulfill({ json: { ok: true, token: "test-token", expires_in: 1800 } }));
  await page.route("**/api/admin/login", (route) => route.fulfill({ json: { ok: true, token: "test-token", expires_in: 1800 } }));
  await page.route("**/api/config", (route) => route.fulfill({ json: { path: "/tmp/config.json", config: savedConfig } }));
  await page.route("**/api/config/save", async (route) => {
    const request = route.request().postDataJSON();
    savedConfig = request.config;
    await route.fulfill({ json: { ok: true, path: "/tmp/config.json", config: savedConfig } });
  });
  await page.route("**/api/station/search?*", (route) => route.fulfill({ json: { query: "Jahnplatz", results: [{ station_id: "23000001", station_name: "Bielefeld Jahnplatz" }] } }));
  await page.route("**/mock-stream?*", (route) => route.fulfill({ contentType: "text/html", body: "<title>Mock stream</title><main>Stream</main>" }));
  return () => savedConfig;
}

for (const viewport of [
  { width: 1024, height: 600, expected: "minimal" },
  { width: 1280, height: 720, expected: "standard" },
  { width: 1920, height: 1080, expected: "information" },
]) {
  test(`livestream-first layout at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockBackend(page);
    await page.goto("/");
    await expect(page.locator("body")).toHaveAttribute("data-layout", viewport.expected);
    const stage = await page.locator("#stage").boundingBox();
    expect(stage.width).toBe(viewport.width);
    expect(stage.height).toBe(viewport.height);
    await expect(page.locator("#clock")).toBeVisible();
    await expect(page.locator("#weatherText")).toContainText("21 °C");
    const cards = page.locator("#radar, #transitPanel");
    for (let index = 0; index < await cards.count(); index += 1) {
      const card = cards.nth(index);
      if (!(await card.isVisible())) continue;
      const box = await card.boundingBox();
      expect(box).not.toBeNull();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.y).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
      expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1);
    }
  });
}

test("admin PIN setup, station add and save without stream reload", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const getSaved = await mockBackend(page);
  let iframeNavigations = 0;
  page.on("framenavigated", (frame) => { if (frame !== page.mainFrame()) iframeNavigations += 1; });
  await page.goto("/");
  await page.keyboard.press("Control+Alt+S");
  await expect(page.locator("#pinDialog")).toBeVisible();
  await page.locator("#adminPin").fill("1234");
  await page.locator("#adminPinConfirm").fill("1234");
  await page.locator("#submitPin").click();
  await expect(page.locator("#settingsDialog")).toBeVisible();
  await page.locator("#stationQuery").fill("Jahnplatz");
  await page.locator("#stationSearchBtn").click();
  await page.getByRole("button", { name: "Hinzufügen" }).click();
  await expect(page.locator(".stop-card")).toHaveCount(1);
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
  await expect(page.locator("#radarStatus")).toHaveText("Radar offline");
  await expect(page.locator("#sys")).toContainText("CPU –");
  await expect(page.locator("#streamStatusText")).toContainText("Wiedergabe nicht verifizierbar");
});
