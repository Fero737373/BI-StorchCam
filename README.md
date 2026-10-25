# BI-StorchCam

BI-StorchCam ist ein leichtgewichtiger lokaler Web-Kiosk für einen Livestream mit Uhr, Wetter, Regenradar und optionalen VRR-Abfahrten. Der Livestream bleibt die Hauptfläche; Zusatzinformationen liegen kompakt an den Bildschirmrändern.

> **Status:** `0.2.0-beta.1`. Der Quellstand ist für einen ersten Beta-Test gehärtet.

## Screenshots

Die automatisierten UI-Tests erzeugen bei Fehlern Screenshots für 1024×600, 1280×720 und 1920×1080. Produktive Referenzscreenshots werden nach dem ersten bestandenen Pi-Hardwaretest ergänzt.

## Funktionen

- eine einzige Web-Kiosk-Architektur und ein zentraler Einstiegspunkt
- Livestream mit ehrlichen Lade- und Fehlerzuständen
- Layoutprofile `minimal`, `standard`, `information` und Viewport-Auswahl über `auto`
- Open-Meteo-Wetter ab der aktuellen Uhrzeit
- RainViewer-Radar mit Datenzeit, Quelle, Standortmarkierung und Offlinezustand
- mehrere VRR-Haltestellen mit Linien- und Nachtbusfiltern
- lokaler Adminmodus per drei Sekunden langer Berührung oben links oder `Ctrl+Alt+S`
- PBKDF2-gehashte PIN und zeitlich begrenzte Admin-Sessions
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

Für Live-Daten benötigt BI-StorchCam Netzwerkzugriff zu Open-Meteo, RainViewer, OpenStreetMap-Kacheln und dem VRR-Haltestellenmonitor. Der Stream benötigt Zugriff auf die konfigurierte Streamdomain. Die App enthält keine Cloud-Benutzerverwaltung und sendet keine lokale PIN.

## Docker

```bash
git clone https://github.com/Fero737373/BI-StorchCam.git
cd BI-StorchCam
mkdir -p data
BI_STORCHCAM_ADMIN_PIN=1234 \
BI_STORCHCAM_STREAM_URL="https://…/embed" \
docker compose up -d --build
```

Die PIN (4–12 Ziffern) wird nur beim allerersten Start benötigt und als PBKDF2-Hash in `./data/config.json` gespeichert. Alternativ interaktiv einrichten:

```bash
docker compose run --rm bi-storchcam --setup
docker compose up -d
```

Voraussetzungen für die Anzeige auf dem Bildschirm:

- Desktop-Autologin für den Benutzer mit UID 1000 (Wayland-Socket `/run/user/1000/wayland-0`)
- Der Container bindet `/run/user` (Wayland, Audio) und `/dev/dri` (GPU) ein und läuft mit `seccomp=unconfined`, damit die Chromium-Sandbox aktiv bleiben kann.
- Startet Docker beim Booten vor der Desktop-Sitzung, wartet der Container bis zu fünf Minuten auf den Wayland-Socket.

Mit `restart: unless-stopped` startet die Cam nach jedem Neustart automatisch. `docker compose stop` schließt den Kiosk wieder. `BI_STORCHCAM_KIOSK=0` startet nur den Server (Aufruf dann z. B. über `http://<pi>:8000/`). `BI_STORCHCAM_STREAM_URL` überschreibt bei jedem Start die Stream-URL; ohne die Variable gilt der Wert aus `./data/config.json` bzw. dem Adminmodus.

Diagnoseoptionen laufen ebenfalls im Container:

```bash
docker compose run --rm bi-storchcam --test-config
docker compose run --rm bi-storchcam --test-weather
docker compose run --rm bi-storchcam --station-search "Jahnplatz"
```

Ohne Docker: `python -m pip install -e .` und `python -m bi_storchcam --no-browser`.

## Adminzugriff

Halte die unsichtbare obere linke Ecke mindestens drei Sekunden gedrückt oder drücke `Ctrl+Alt+S`. Beim ersten lokalen Aufruf wird eine PIN mit 4 bis 12 Ziffern festgelegt. Gespeichert wird nur ein PBKDF2-SHA256-Hash mit individuellem Salt. Schreibzugriffe erfordern anschließend ein zeitlich begrenztes In-Memory-Token.

Der Server bindet standardmäßig ausschließlich an `127.0.0.1`. Vor einer externen Bind-Adresse muss bereits eine Admin-PIN eingerichtet sein.

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
- Regenradar: [RainViewer](https://www.rainviewer.com/)
- Basiskarte: [OpenStreetMap-Mitwirkende](https://www.openstreetmap.org/copyright)
- ÖPNV: VRR-Haltestellenmonitor

Die Kartenattribution wird zusätzlich im Radarbereich angezeigt. Marken und Logos werden nicht unnötig eingebunden.

## Lizenz

Der Quellcode steht weiterhin unter [GPL-3.0-only](LICENSE). Daten und Karten unterliegen den Bedingungen der jeweiligen Anbieter.
