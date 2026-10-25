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
| `location.latitude` / `longitude` | Wetterposition | −90…90 / −180…180 |
| `stream.url` | Embed-URL; normale YouTube-Links werden in die Embed-Form umgewandelt | leer oder vollständiges HTTP(S) |
| `stream.autoplay` / `muted` | Playerparameter | boolesch |
| `admin.pin_hash` | lokaler PBKDF2-Hash | nur durch Setup setzen |
| `admin.require_pin` | Menü nur mit PIN öffnen; im Docker-Container per `BI_STORCHCAM_REQUIRE_PIN` gesetzt | `true`, Docker: `false` |
| `youtube.api_key` | optionaler Schlüssel für die YouTube Data API v3; wird nie an die Oberfläche ausgeliefert, leer = öffentliche Suchseite oder `YOUTUBE_API_KEY` | leer |
| `youtube.default_query` | Suchwort beim Öffnen der Livestream-Auswahl | `Storch` |
| `ui.theme` | Farbsystem; `y2k` zeigt tagsüber ziehende Wolken, nachts funkelnde Sterne; `dagobert` ist ein Comic-Geldspeicher mit fallenden Talern am Tag und Sternenhimmel bei Nacht (Tag/Nacht laut Open-Meteo) | `dark`, `light`, `high-contrast`, `y2k`, `dagobert` |
| `ui.sky` | Tag/Nacht der Themes `y2k` und `dagobert`: automatisch nach Sonnenstand (Open-Meteo) oder fest | `auto`, `day`, `night` |
| `music.source` | Quelle für „Läuft gerade“ oben rechts | `off`, `auto` (Spotify, sonst YouTube Music), `spotify`, `ytmusic` (Anmeldung im Menü unter Musik, siehe API_NOTES) |
| `music.spotify.client_id` | Client-ID der eigenen Spotify-App (Redirect URI: `http://127.0.0.1:<Port>/api/music/spotify/callback`) | Text |
| `ui.layout_profile` | Informationsdichte | `auto`, `minimal`, `standard`, `information` |
| `ui.*.enabled` | Uhr/Wetter/ÖPNV/System in der Infoleiste; ausgeschaltete Blöcke entfallen samt Trenner | boolesch |
| `weather.provider` | Wetterprovider | derzeit `openmeteo` |
| `weather.refresh_seconds` | Wetterintervall | 60–3600 Sekunden |
| `weather.forecast_hours` | Zukunftsfenster | 1–48 Stunden |
| `weather.rain_mm_threshold` | Regenmenge-Grenze | 0–100 mm |
| `weather.rain_probability_threshold` | Wahrscheinlichkeitsgrenze; beide Schwellen bestimmen die Regenzusammenfassung („Regen ab …“) | 0–100 % |
| `transit.provider` | ÖPNV-Provider | derzeit `vrr` |
| `transit.refresh_seconds` | Abfahrtsintervall | 15–3600 Sekunden |
| `transit.default_max_rows` | Standardzeilen | 1–12 |
| `transit.target_len` | Ziellängenkürzung | 8–80 Zeichen |
| `transit.stops` | bis zu 20 Haltestellen | Liste, siehe unten |
| `logging.level` | App-Loglevel | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `logging.max_bytes` / `backups` | App-Logrotation | 64 KiB–100 MiB / 1–20 |

Eine Haltestelle enthält `title`, `station_name`, `station_id`, `line_filter`, `nightbus_only`, `hide_if_empty` und `max_rows`. Die Oberfläche verwaltet diese Felder ohne manuelle JSON-Bearbeitung. Der VRR-Provider gilt nur für seine unterstützte Region.

Die Infoleiste zeigt höchstens drei Abfahrten (unter 760 px Breite zwei) über alle Haltestellen hinweg, nach Minuten sortiert. `max_rows` begrenzt weiterhin, wie viele Zeilen je Haltestelle abgefragt werden.

Im Theme `dagobert` steht eine Comicfigur auf der Infoleiste (tagsüber mit Taler, nachts mit Schlafmütze). Eigene Bilder ersetzen die mitgelieferte Zeichnung: `dagobert-tag` und `dagobert-nacht` als `.png`, `.webp` oder `.svg` in den Ordner `theme/` neben der `config.json` legen (Docker: `data/theme/`). Am besten eignen sich freigestellte Bilder mit transparentem Hintergrund.

Das frühere Regenradar wurde entfernt. Alte Konfigurationen mit `ui.radar` oder `radar` werden beim Start automatisch bereinigt.
