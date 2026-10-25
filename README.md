# BI-StorchCam

BI-StorchCam ist ein leichtgewichtiger lokaler Web-Kiosk für einen Livestream mit Uhr, Wetter und optionalen VRR-Abfahrten. Der Livestream füllt den ganzen Bildschirm; alle Zusatzinformationen liegen in einer Infoleiste am unteren Rand.

> **Status:** `0.2.0-beta.1`. Der Quellstand ist für einen ersten Beta-Test gehärtet.

## Screenshots

Die automatisierten UI-Tests erzeugen bei Fehlern Screenshots für 1024×600, 1280×720 und 1920×1080. Referenzbilder mit Mock-Daten (alle Profile, Themes und Fehlerzustände) entstehen auf Wunsch:

```bash
SCREENSHOT_DIR=/tmp/storchcam-shots npx playwright test -g "reference screenshots"
```

Produktive Referenzscreenshots werden nach dem ersten bestandenen Pi-Hardwaretest ergänzt.

## Funktionen

- eine einzige Web-Kiosk-Architektur und ein zentraler Einstiegspunkt
- vollflächiger Livestream ohne Einblendungen; nur bei Fehlern erscheint ein Hinweis
- Infoleiste unten aus Milchglas: Uhr mit Datum und Systemzeile, Wetter mit Stundenleiste der Regenwahrscheinlichkeit und die nächsten drei Abfahrten
- Layoutprofile `minimal`, `standard`, `information` und Viewport-Auswahl über `auto`; ausgeschaltete Blöcke verschwinden samt Trenner
- Themes `dark`, `light`, `high-contrast`, alle Texte mit mindestens 4,5:1 Kontrast
- Schrift Barlow lokal eingebunden (SIL OFL 1.1), funktioniert offline
- Open-Meteo-Wetter ab der aktuellen Uhrzeit, Regenstunden nach den konfigurierten Schwellen
- mehrere VRR-Haltestellen mit Linien- und Nachtbusfiltern; Abfahrten aller Haltestellen nach Minuten sortiert
- Menü-Knopf oben links (oder `Ctrl+Alt+S`) mit Touch-Oberfläche und Bildschirmtastatur
- Livestream-Auswahl aus allem, was gerade auf YouTube live ist, ohne API-Schlüssel
- weltweite Ortssuche; Uhr und Wetter folgen der Zeitzone des Orts
- im Docker-Betrieb ohne PIN, sonst PBKDF2-gehashte PIN und zeitlich begrenzte Admin-Sessions
- Hintergrund-State ohne Provideraufrufe pro Browseranfrage
- überwachte Chromium-, Chrome- oder Edge-Prozesse mit begrenztem Backoff
- atomische Konfiguration mit letzter Sicherung
- rotierende App- und Browserlogs
- Docker-Container mit Healthcheck und automatischem Neustart

## Betrieb

BI-StorchCam läuft als Docker-Container (getestet auf Raspberry Pi OS / Debian 13, ARM64, labwc/Wayland). Der Container startet Server und Chromium-Kiosk; Chromium erscheint direkt auf dem angeschlossenen Bildschirm.

## Bekannte Einschränkungen

- Eine fremde Stream-Plattform kann Einbettung per CSP oder `X-Frame-Options` blockieren. Ein geladenes `iframe` wird deshalb nicht als bestätigte Wiedergabe bezeichnet.
- ÖPNV basiert aktuell auf dem VRR-Haltestellenmonitor. Andere Regionen werden nicht allgemein als unterstützt beworben.
- Wayland-Displayrotation wird nicht automatisch verändert. Hardwareprofile wenden Rotation nur sicher unter X11 an.
- Windows stellt Temperaturwerte nur dar, wenn sie tatsächlich verfügbar sind; andernfalls erscheint `–` beziehungsweise „nicht verfügbar“.
- Der reale achtstündige Pi-Test und die visuelle Abnahme am Zielbildschirm müssen vor einer stabilen Version erfolgen.

## Externe Dienste

Für Live-Daten benötigt BI-StorchCam Netzwerkzugriff zu Open-Meteo (Wetter, Ortssuche, Zeitzone), Nominatim/OpenStreetMap (Adresssuche), dem VRR-Haltestellenmonitor und für die Livestream-Suche zu YouTube (öffentliche Suchseite bzw. YouTube Data API, Vorschaubilder von i.ytimg.com). Der Stream benötigt Zugriff auf die konfigurierte Streamdomain. Die App enthält keine Cloud-Benutzerverwaltung und sendet keine lokale PIN.

## Docker

```bash
git clone https://github.com/Fero737373/BI-StorchCam.git
cd BI-StorchCam
mkdir -p data
docker compose up -d --build
```

Mehr ist nicht nötig: kein API-Schlüssel, keine PIN. Der Container startet Server und Chromium-Kiosk; die Anzeige erscheint im Vollbild direkt auf dem angeschlossenen Bildschirm. Zusätzlich ist sie auf dem Gerät selbst unter `http://localhost:8080` erreichbar (bewusst nicht aus dem Netzwerk, weil das Menü keine PIN hat).

Nach Codeänderungen immer mit `--build` starten, sonst läuft das alte Image weiter.

Voraussetzungen für die Anzeige auf dem Bildschirm:

- Desktop-Autologin für den Benutzer mit UID 1000 (Wayland-Socket `/run/user/1000/wayland-0`)
- Der Container bindet `/run/user` (Wayland, Audio) und `/dev/dri` (GPU) ein und läuft mit `seccomp=unconfined`, damit die Chromium-Sandbox aktiv bleiben kann.
- Startet Docker beim Booten vor der Desktop-Sitzung, wartet der Container bis zu fünf Minuten auf den Wayland-Socket.

Optionale Umgebungsvariablen (z. B. in einer `.env` neben `docker-compose.yml`):

| Variable | Wirkung |
| --- | --- |
| `BI_STORCHCAM_STREAM_URL` | setzt bei jedem Start die Stream-URL |
| `YOUTUBE_API_KEY` | nutzt für die Live-Suche die offizielle YouTube-API statt der öffentlichen Suchseite |
| `BI_STORCHCAM_KIOSK=0` | nur Server, kein Browser auf dem Bildschirm |
| `BI_STORCHCAM_REQUIRE_PIN=1` + `BI_STORCHCAM_ADMIN_PIN` | Menü wieder mit PIN schützen |

Diagnoseoptionen laufen ebenfalls im Container, z. B. `docker compose run --rm bi-storchcam --test-weather`.

Ohne Docker: `python -m pip install -e .` und `python -m bi_storchcam --no-browser`.

## Menü

Der Knopf oben links öffnet das Menü. Alles ist per Touch bedienbar, Texteingaben laufen über die eingebaute Bildschirmtastatur.

- **Livestream:** zeigt Streams, die gerade auf YouTube live sind (Start mit „Storch“, Suchwort frei wählbar). Antippen spielt den Stream sofort ab. Ohne Schlüssel liest die App die öffentliche YouTube-Suche mit dem Filter „Live“; ändert YouTube diese Seite, kann die Suche ausfallen, bis die App angepasst ist. Manche Kanäle verbieten das Einbetten; dann zeigt der Player einen Hinweis.
- **Ort:** weltweite Suche nach Adresse, Straße oder Ort (Nominatim/OpenStreetMap, Rückfall auf Open-Meteo). Antippen übernimmt Name, Koordinaten und Zeitzone; Uhr und Wetter folgen.
- **Anzeige:** Layoutprofil, Theme, sichtbare Blöcke.
- **ÖPNV:** Haltestellen, derzeit nur im VRR (Nordrhein-Westfalen).
- **System:** optionaler YouTube-API-Schlüssel und Start-Suchwort.

## Adminzugriff außerhalb von Docker

Ohne Docker bleibt das Menü PIN-geschützt (`admin.require_pin`). Beim ersten Öffnen wird eine PIN mit 4 bis 12 Ziffern festgelegt; gespeichert wird nur ein PBKDF2-SHA256-Hash. Der Server bindet dann standardmäßig ausschließlich an `127.0.0.1`.

## Konfiguration und Logs

- Konfiguration: `./data/config.json` (im Container `/data/config.json`, Override per `BI_STORCHCAM_CONFIG`)
- Letzte Sicherung: `./data/config.json.bak`
- App-Log: `./data/.cache/BI-StorchCam/storchcam.log` bzw. `docker compose logs -f`

Eine ungültige Originaldatei wird nicht still überschrieben. Alle Felder sind in [docs/CONFIGURATION.md](docs/CONFIGURATION.md) beschrieben.

## Tests

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy bi_storchcam
pytest -q
npm ci
npx playwright install chromium
npm run test:ui
```

Playwright verwendet gemockte API-Antworten und ruft keine echten externen Provider auf.

## Datenschutz und Netzwerk

BI-StorchCam verarbeitet Standort, Stream-URL und Haltestellen lokal. Externe Anbieter erhalten technisch notwendige Netzwerkdaten wie IP-Adresse und angefragte Koordinaten beziehungsweise Haltestellen. Eine externe Serverbindung sollte nur in einem vertrauenswürdigen Netz und mit eingerichteter PIN verwendet werden.

## Datenquellen und Attribution

- Wetter: [Open-Meteo](https://open-meteo.com/)
- Adresssuche: [Nominatim](https://nominatim.org/), Daten © [OpenStreetMap-Mitwirkende](https://www.openstreetmap.org/copyright)
- ÖPNV: VRR-Haltestellenmonitor

Marken und Logos werden nicht unnötig eingebunden.

## Lizenz

Der Quellcode steht weiterhin unter [GPL-3.0-only](LICENSE). Daten unterliegen den Bedingungen der jeweiligen Anbieter.
