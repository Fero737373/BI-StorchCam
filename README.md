# BI-StorchCam

BI-StorchCam ist ein leichtgewichtiger lokaler Web-Kiosk für einen Livestream mit Uhr, Wetter, Regenradar und optionalen VRR-Abfahrten. Der Livestream bleibt die Hauptfläche; Zusatzinformationen liegen kompakt an den Bildschirmrändern.

> **Status:** `0.2.0-beta.1`. Der Quellstand ist für einen ersten Beta-Test gehärtet. Ein mindestens achtstündiger Raspberry-Pi-Hardwaretest steht noch aus und wird nicht als bestanden behauptet.

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
- dezenter lokaler Start-/Stop-Schalter für Pegasus auf dem HDMI-Ausgang
- PBKDF2-gehashte PIN und zeitlich begrenzte Admin-Sessions
- Hintergrund-State ohne Provideraufrufe pro Browseranfrage
- überwachte Chromium-, Chrome- oder Edge-Prozesse mit begrenztem Backoff
- atomische Konfiguration mit letzter Sicherung
- rotierende App- und Browserlogs
- systemd-User-Service für unbeaufsichtigten Betrieb

## Unterstützte Plattformen

| Plattform | Stand |
| --- | --- |
| Raspberry Pi OS 64-Bit | Zielplattform; finaler Hardware-Soak-Test offen |
| Linux x64 | Python- und PyInstaller-CI vorgesehen |
| Windows x64 | Python- und PyInstaller-CI vorgesehen |
| Linux ARM64 | lokaler Build auf ARM64 vorgesehen; kein Cross-Build-Versprechen |

Python 3.10 bis 3.13 werden in der CI-Matrix geprüft. Der Kioskmanager unterstützt Chromium, Google Chrome und Microsoft Edge. Firefox wird bewusst nicht mit inkompatiblen Chromium-Flags gestartet.

## Bekannte Einschränkungen

- Eine fremde Stream-Plattform kann Einbettung per CSP oder `X-Frame-Options` blockieren. Ein geladenes `iframe` wird deshalb nicht als bestätigte Wiedergabe bezeichnet.
- ÖPNV basiert aktuell auf dem VRR-Haltestellenmonitor. Andere Regionen werden nicht allgemein als unterstützt beworben.
- Wayland-Displayrotation wird nicht automatisch verändert. Hardwareprofile wenden Rotation nur sicher unter X11 an.
- Windows stellt Temperaturwerte nur dar, wenn sie tatsächlich verfügbar sind; andernfalls erscheint `–` beziehungsweise „nicht verfügbar“.
- Der reale achtstündige Pi-Test und die visuelle Abnahme am Zielbildschirm müssen vor einer stabilen Version erfolgen.

## Externe Dienste

Für Live-Daten benötigt BI-StorchCam Netzwerkzugriff zu Open-Meteo, RainViewer, OpenStreetMap-Kacheln und dem VRR-Haltestellenmonitor. Der Stream benötigt Zugriff auf die konfigurierte Streamdomain. Die App enthält keine Cloud-Benutzerverwaltung und sendet keine lokale PIN.

## Raspberry-Pi-Installation

```bash
git clone https://github.com/Fero737373/BI-StorchCam.git
cd BI-StorchCam
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python launcher.py --setup
python launcher.py --no-browser
```

Nach erfolgreichem Server-Test:

```bash
bash scripts/install_systemd_user.sh
systemctl --user status bi-storchcam.service
```

Für den Pegasus-Schalter wird `KonsolenDocker` standardmäßig unter
`~/KonsolenDocker` erwartet. Ein anderer absoluter Pfad lässt sich vor dem
StorchCam-Start über `STORCHCAM_CONSOLE_CONTROL` setzen:

```bash
export STORCHCAM_CONSOLE_CONTROL=/home/fero/KonsolenDocker/bin/console-control
```

Die HTTP-Steuerung akzeptiert ausschließlich lokale Loopback-Anfragen. Der
Docker-Aufbau und die einmalige Host-Erkennung erfolgen vorher mit
`KonsolenDocker/bin/setup`; der UI-Schalter baut beim Antippen kein Image.

Für User-Services kann auf einem unbeaufsichtigten Gerät zusätzlich `loginctl enable-linger "$USER"` mit passenden Administratorrechten nötig sein. Das optionale Desktop-Autostart-Script `scripts/install_linux_autostart.sh` ist nur ein weniger robuster Fallback.

## Linux-Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m bi_storchcam --setup
python -m bi_storchcam
```

## Windows-Installation

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python launcher.py --setup
python launcher.py
```

## Einheitliche Startbefehle

Alle drei Befehle starten dieselbe Anwendung:

```bash
python launcher.py
python -m bi_storchcam
bi-storchcam
```

Mit `--no-browser` läuft nur der lokale Server. `--test-config`, `--test-weather`, `--test-radar`, `--test-transit` und `--station-search "Name"` sind Diagnoseoptionen.

## Adminzugriff

Halte die unsichtbare obere linke Ecke mindestens drei Sekunden gedrückt oder drücke `Ctrl+Alt+S`. Beim ersten lokalen Aufruf wird eine PIN mit 4 bis 12 Ziffern festgelegt. Gespeichert wird nur ein PBKDF2-SHA256-Hash mit individuellem Salt. Schreibzugriffe erfordern anschließend ein zeitlich begrenztes In-Memory-Token.

Der Server bindet standardmäßig ausschließlich an `127.0.0.1`. Vor einer externen Bind-Adresse muss bereits eine Admin-PIN eingerichtet sein.

## Konfiguration

- Linux/Raspberry Pi: `~/.config/BI-StorchCam/config.json`
- Windows: `%APPDATA%\BI-StorchCam\config.json`
- macOS: `~/Library/Application Support/BI-StorchCam/config.json`
- Override: Umgebungsvariable `BI_STORCHCAM_CONFIG`

Die letzte vorherige Datei liegt als `config.json.bak` daneben. Eine ungültige Originaldatei wird nicht still überschrieben. Alle Felder sind in [docs/CONFIGURATION.md](docs/CONFIGURATION.md) beschrieben.

## Diagnose und Logs

```bash
bash scripts/diagnose.sh
```

Das Script schreibt einen redigierten Einzelbericht nach `~/.cache/BI-StorchCam/diagnose-*.txt`. Adminhash und PIN werden nicht ausgegeben.

- App: `~/.cache/BI-StorchCam/storchcam.log`
- Browser: `~/.cache/BI-StorchCam/chromium.log`
- Service: `journalctl --user -u bi-storchcam.service`

## Build

Die gemeinsame `BI-StorchCam.spec` enthält HTML, CSS und JavaScript und löst Ressourcen im Python- sowie PyInstaller-Betrieb auf.

```bash
bash build_linux.sh
```

Unter Windows:

```bat
build_windows.bat
```

Windows-Binaries müssen auf Windows, Linux-x64-Binaries auf Linux x64 und ARM64-Binaries lokal auf ARM64 gebaut werden. Es werden keine ungeprüften Binärdateien im Repository veröffentlicht.

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

Playwright verwendet gemockte API-Antworten und ruft keine echten externen Provider auf. Details zum achtstündigen Test stehen in [docs/SOAK_TEST.md](docs/SOAK_TEST.md).

## Deinstallation

```bash
bash scripts/remove_systemd_user.sh
bash scripts/remove_linux_autostart.sh
```

Konfiguration und Logs bleiben bewusst erhalten. Sie können anschließend gezielt aus den oben genannten Pfaden entfernt werden.

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
