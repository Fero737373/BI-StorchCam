# BI-StorchCam

**Status:** Preview/Beta. Das Projekt ist für einen ersten Test-Release vorbereitet, aber noch kein finales Produkt.

**BI-StorchCam** ist ein Open-Source-Infoscreen für Bielefeld. Die App startet einen lokalen Webserver, öffnet einen Browser im Kiosk-Modus und zeigt über dem Livestream gut lesbare Infos:

- Uhrzeit
- Wetter für Bielefeld bzw. den konfigurierten Standort
- Regenradar
- moBiel-/VRR-Abfahrten
- optionale Technikdaten für Diagnose

Der Standard-Livestream ist voreingestellt und kann im Menü geändert werden. Für Release-Abnahmen gibt es zusätzlich die Datei [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

## Unterstützte Systeme

- Windows 10/11 mit Microsoft Edge oder Google Chrome
- Linux Desktop mit Chromium/Chrome/Edge/Firefox
- Raspberry Pi OS / Debian mit Chromium

Die App versucht den Browser automatisch zu finden. Unter Windows werden Edge und Chrome automatisch gesucht. Unter Linux werden typische Browser-Binaries wie `chromium`, `chromium-browser`, `google-chrome` und `firefox` gesucht.

## Installation aus dem Sourcecode

### Windows

Voraussetzungen:

- Python 3.10 oder neuer
- Microsoft Edge oder Google Chrome

Im Projektordner:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py --test-config
python launcher.py
```

Nur den Server ohne Browser starten:

```powershell
python launcher.py --no-browser
```

Regenradar testen:

```powershell
python launcher.py --test-radar
```

### Linux / Raspberry Pi OS

Voraussetzungen auf Debian/Ubuntu/Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3 python3-venv chromium
```

Im Projektordner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py --test-config
python launcher.py
```

Nur den Server ohne Browser starten:

```bash
python launcher.py --no-browser
```

Regenradar testen:

```bash
python launcher.py --test-radar
```

## Konfiguration

Die App erstellt die lokale Konfiguration automatisch.

Windows:

```text
%APPDATA%\BI-StorchCam\config.json
```

Linux / Raspberry Pi:

```text
~/.config/BI-StorchCam/config.json
```

Wichtige Einstellungen:

```json
{
  "kiosk": {
    "browser": "auto",
    "profile_dir": ""
  },
  "location": {
    "label": "Bielefeld",
    "latitude": 52.0302,
    "longitude": 8.5325
  },
  "ui": {
    "weather": {"enabled": true},
    "radar": {
      "enabled": true,
      "zoom": 10,
      "refresh_seconds": 300
    },
    "transit": {"enabled": false},
    "system": {"enabled": false}
  }
}
```

Wenn `browser` auf `auto` steht, sucht BI-StorchCam selbst nach einem passenden Browser. Ein fester Pfad ist weiterhin möglich, z. B. unter Linux `/usr/bin/chromium` oder unter Windows `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## Release-Default

Für einen sauberen öffentlichen Preview-Screen sind im Standard nur Uhrzeit, Wetter und Regenradar sichtbar. Abfahrten werden erst angezeigt, wenn im Menü eine echte Haltestelle übernommen und gespeichert wurde. Systemdaten sind im Standard ausgeblendet und nur für Diagnose gedacht.

## Regenradar

Das Regenradar wird über RainViewer geladen. Die App fragt serverseitig die aktuellen Radar-Frames ab und rendert im Browser Kacheln rund um den konfigurierten Standort. Wenn RainViewer oder das Netzwerk nicht erreichbar ist, bleibt die App offen und zeigt einen Offline-Hinweis im Radar-Feld statt abzustürzen.

## Windows-EXE erstellen

```powershell
build_windows.bat
```

Die fertige Datei liegt danach hier:

```text
dist\BI-StorchCam.exe
```

## Linux-Binary erstellen

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Die fertige Datei liegt danach hier:

```text
dist/BI-StorchCam
```

## Linux-Autostart einrichten

```bash
chmod +x scripts/install_linux_autostart.sh
./scripts/install_linux_autostart.sh
```

Autostart wieder entfernen:

```bash
chmod +x scripts/remove_linux_autostart.sh
./scripts/remove_linux_autostart.sh
```

## Troubleshooting

### Windows: „Chromium nicht gefunden“

Aktuelle Version starten und sicherstellen, dass Edge oder Chrome installiert ist:

```powershell
python launcher.py --test-config
python launcher.py
```

Die App sucht Edge/Chrome automatisch. Falls trotzdem kein Browser startet, kann in der lokalen `config.json` ein fester Browser-Pfad gesetzt werden.

### Windows: `hostname -s` oder `hostname -I` Fehler

Diese Fehler sollten nicht mehr auftreten. Die App nutzt keine Linux-only-Hostname-Flags mehr, sondern ermittelt die lokale IP plattformneutral.

### Regenradar lädt nicht

```bash
python launcher.py --test-radar
```

Wenn `ok` false ist, liegt es meistens an Netzwerk/DNS/Firewall oder RainViewer ist kurzfristig nicht erreichbar. Die UI läuft trotzdem weiter.

## Bielefeld-Fokus

Dieses Projekt ist bewusst auf Bielefeld ausgelegt. Die Haltestellensuche nutzt den VRR-Haltestellenmonitor und ist für moBiel/VRR-Haltestellen gedacht.

## Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0. Siehe `LICENSE`.
