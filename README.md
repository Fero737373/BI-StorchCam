# BI-StorchCam

**BI-StorchCam** ist ein Open-Source-Infoscreen für Bielefeld. Die App zeigt einen Livestream im Hintergrund und legt darüber große, gut lesbare Informationen:

- Uhrzeit oben
- Wetter für den eingegebenen Ort in Bielefeld unten
- moBiel-/ÖPNV-Abfahrten einer bestätigten Haltestelle rechts unten über dem Wetter

Der Standard-Livestream ist bereits voreingestellt, kann aber im Setup durch einen anderen YouTube- oder Webcam-Link ersetzt werden.

## Ziel

Die App soll einfach bedienbar sein:

1. App starten.
2. Ort oder Adresse in Bielefeld eingeben.
3. Haltestelle suchen lassen.
4. Gefundene Haltestelle bestätigen.
5. Wenn die Haltestelle falsch ist, Haltestellennamen manuell eingeben und erneut suchen.
6. Infoscreen starten.

## Screenshot-Logik

Das Design orientiert sich an einem dunklen Kiosk-Screen:

- oben: große Uhrzeit
- rechts unten: schwarzes Abfahrtspanel mit gelber Schrift
- unten: schwarze Wetterleiste mit weißer Schrift
- Livestream im Hintergrund

Technische Daten wie IP, CPU oder RAM werden absichtlich nicht angezeigt.

## Unterstützte Datenquellen

### Wetter

Wetterdaten werden über Open-Meteo geholt. Für die Eingabe einer Adresse oder eines Ortes wird eine Geokodierung benutzt. Wenn keine genaue Adresse gefunden wird, fällt die App auf Bielefeld zurück.

### Abfahrten

Die Abfahrten werden über den VRR-Haltestellenmonitor geladen. Für Bielefeld/moBiel funktioniert das mit Haltestellen wie zum Beispiel:

- Gellershagen Schneiderstraße
- Bielefeld Bi-Gellershagen, Schneiderstr

Die App speichert die bestätigte Haltestelle in der lokalen Konfigurationsdatei.

## Projektstruktur

```text
BI-StorchCam/
├─ bi_storchcam/
│  ├─ __init__.py
│  ├─ __main__.py
│  ├─ app.py
│  ├─ browser.py
│  ├─ config.py
│  ├─ geocoding.py
│  ├─ overlay.py
│  ├─ setup_wizard.py
│  └─ providers/
│     ├─ __init__.py
│     ├─ transit_vrr.py
│     └─ weather_openmeteo.py
├─ scripts/
│  ├─ install_linux_autostart.sh
│  └─ remove_linux_autostart.sh
├─ launcher.py
├─ requirements.txt
├─ build_windows.bat
├─ build_linux.sh
├─ config.example.json
├─ LICENSE
└─ README.md
```

## Installation aus dem Sourcecode

### Windows

Voraussetzungen:

- Python 3.10 oder neuer
- Google Chrome oder Microsoft Edge für den Livestream

Im Projektordner:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py --setup
```

Danach kann die App normal gestartet werden:

```powershell
python launcher.py
```

## Windows-EXE erstellen

Im Projektordner:

```powershell
build_windows.bat
```

Die fertige Datei liegt danach hier:

```text
dist\BI-StorchCam.exe
```

Falls Windows SmartScreen warnt: Das ist normal bei selbstgebauten EXE-Dateien ohne Signatur. Für öffentliche Releases sollte die EXE später signiert werden.

## Linux starten

Voraussetzungen auf Debian/Ubuntu/Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk chromium
```

Dann im Projektordner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py --setup
```

Danach starten:

```bash
python launcher.py
```

## Linux-Binary erstellen

Im Projektordner:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Die fertige Datei liegt danach hier:

```text
dist/BI-StorchCam
```

## Linux-Autostart einrichten

Ohne spezielle Display-Rotation und ohne Touchscreen-Matrix:

```bash
chmod +x scripts/install_linux_autostart.sh
./scripts/install_linux_autostart.sh
```

Autostart wieder entfernen:

```bash
chmod +x scripts/remove_linux_autostart.sh
./scripts/remove_linux_autostart.sh
```

## Konfiguration

Die Konfiguration wird automatisch gespeichert.

Unter Windows:

```text
%APPDATA%\BI-StorchCam\config.json
```

Unter Linux:

```text
~/.config/BI-StorchCam/config.json
```

Setup erneut öffnen:

```bash
python launcher.py --setup
```

Overlay ohne Browser starten, nur zum Testen:

```bash
python launcher.py --no-browser
```

## Standard-Livestream

Voreingestellt ist:

```text
https://www.youtube.com/watch?v=mRECZ-PJ2So
```

Im Setup kann jeder andere YouTube- oder Webcam-Link eingetragen werden.

## Hinweise zu YouTube

Manche YouTube-Livestreams erlauben kein Einbetten in eigene HTML-Seiten. BI-StorchCam öffnet deshalb den normalen YouTube-Link im Browser und legt die eigenen UI-Fenster darüber. Dadurch funktioniert auch ein Stream, der nicht als Embed erlaubt ist.

## Bielefeld-Fokus

Dieses Projekt ist bewusst auf Bielefeld ausgelegt. Die Haltestellensuche nutzt den VRR-Haltestellenmonitor und ist für moBiel/VRR-Haltestellen gedacht.

## Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0. Siehe `LICENSE`.
