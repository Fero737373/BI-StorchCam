# BI-StorchCam

BI-StorchCam ist ein lokaler Infoscreen für Raspberry Pi, Linux und Windows. Die App startet einen lokalen Webserver, öffnet einen Browser im Kiosk-Modus und zeigt Livestream, Uhrzeit, Wetter, Regenradar und optionale ÖPNV-Abfahrten.

## Raspberry Pi Start

Die lokale Konfiguration liegt unter `~/.config/BI-StorchCam/config.json`.

Autostart wird über das Script `scripts/install_linux_autostart.sh` eingerichtet. Der Kiosk-Start läuft über `scripts/start_pi5_touch.sh`.

## Diagnose

- Config testen: `python3 launcher.py --test-config`
- Nur Server starten: `python3 launcher.py --no-browser`
- Radar testen: `python3 launcher.py --test-radar`

## Hinweis

Lokale Pi-Konfigurationen gehören nicht ins Repository. Das Repository enthält nur Code, Defaults und Scripts.
