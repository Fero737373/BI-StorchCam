# Konfigurationsreferenz

Die JSON-Konfiguration wird gegen ein geschlossenes Schema validiert. Unbekannte Felder und unsichere Werte werden abgelehnt.

| Pfad | Bedeutung | Bereich/Standard |
| --- | --- | --- |
| `app.timezone` | Zeitzone für Prognosen | IANA-Name, `Europe/Berlin` |
| `app.cache_dir` | rotierende Logs | `~/.cache/BI-StorchCam` |
| `server.host` | lokale Bind-Adresse | `127.0.0.1` |
| `server.port` | HTTP-Port | 1024–65535, `8000` |
| `server.max_request_bytes` | maximale JSON-Größe | 4 KiB–1 MiB |
| `server.admin_session_minutes` | Token-Laufzeit | 5–240 Minuten |
| `kiosk.enabled` | verwalteten Browser starten | `true` |
| `kiosk.browser` | Browserwahl | `auto`, `chromium`, `chrome`, `edge` oder absoluter Pfad |
| `kiosk.profile_dir` | eigenes Browserprofil | leer = plattformsicherer Standard |
| `kiosk.disable_screensaver` | X11-Bildschirmschoner abschalten | `true` |
| `kiosk.use_gpu` | Hardwarebeschleunigung erlauben | `true` |
| `kiosk.browser_restart_seconds` | erster Backoff | 1–60 Sekunden |
| `kiosk.browser_restart_max_seconds` | maximaler Backoff | 5–600 Sekunden |
| `kiosk.browser_stable_seconds` | Laufzeit bis Zähler-Reset | 10–3600 Sekunden |
| `kiosk.browser_max_failures` | Abbruch der Restartschleife | 1–50 |
| `kiosk.log_file` | Browserlog | `~/.cache/BI-StorchCam/chromium.log` |
| `kiosk.log_max_bytes` / `log_backups` | Browserlogrotation | 2 MiB / 3 |
| `kiosk.extra_flags` | zusätzliche Chromium-Flags | Textliste |
| `screen.hardware_profile` | Hardwareverhalten | `generic`, `raspberry_pi_dsi_portrait`, `raspberry_pi_dsi_landscape`, `custom` |
| `screen.output` | X11-Ausgang | `auto` oder exakter Name |
| `screen.rotation` | X11-Rotation | `none`, `normal`, `left`, `right`, `inverted` |
| `screen.touch_device` | exakter XInput-Name | leer = keine Änderung |
| `screen.touch_matrix` | Transformation | leer = keine Änderung |
| `location.label` | sichtbarer Standort | maximal 120 Zeichen |
| `location.latitude` / `longitude` | Karten- und Wetterposition | −90…90 / −180…180 |
| `stream.url` | Embed-URL | leer oder vollständiges HTTP(S) |
| `stream.autoplay` / `muted` | Playerparameter | boolesch |
| `admin.pin_hash` | lokaler PBKDF2-Hash | nur durch Setup setzen |
| `ui.theme` | Farbsystem | `dark`, `light`, `high-contrast` |
| `ui.layout_profile` | Informationsdichte | `auto`, `minimal`, `standard`, `information` |
| `ui.*.enabled` | Uhr/Wetter/Radar/ÖPNV/System | boolesch |
| `ui.radar.width` / `height` | Radargröße | 200–720 / 140–560 Pixel |
| `ui.radar.zoom` / `opacity` | Kartenausschnitt | 4–14 / 0,25–1,0 |
| `weather.provider` | Wetterprovider | derzeit `openmeteo` |
| `weather.refresh_seconds` | Wetterintervall | 60–3600 Sekunden |
| `weather.forecast_hours` | Zukunftsfenster | 1–48 Stunden |
| `weather.rain_mm_threshold` | Regenmenge-Grenze | 0–100 mm |
| `weather.rain_probability_threshold` | Wahrscheinlichkeitsgrenze | 0–100 % |
| `transit.provider` | ÖPNV-Provider | derzeit `vrr` |
| `transit.refresh_seconds` | Abfahrtsintervall | 15–3600 Sekunden |
| `transit.default_max_rows` | Standardzeilen | 1–12 |
| `transit.target_len` | Ziellängenkürzung | 8–80 Zeichen |
| `transit.stops` | bis zu 20 Haltestellen | Liste, siehe unten |
| `radar.provider` | Radarprovider | derzeit `rainviewer` |
| `radar.refresh_seconds` | Metadatenintervall | 120–3600 Sekunden |
| `logging.level` | App-Loglevel | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `logging.max_bytes` / `backups` | App-Logrotation | 64 KiB–100 MiB / 1–20 |

Eine Haltestelle enthält `title`, `station_name`, `station_id`, `line_filter`, `nightbus_only`, `hide_if_empty` und `max_rows`. Die Oberfläche verwaltet diese Felder ohne manuelle JSON-Bearbeitung. Der VRR-Provider gilt nur für seine unterstützte Region.
