# BI-StorchCam

BI-StorchCam ist ein lokaler Infoscreen für Raspberry Pi, Linux und Windows. Die App startet einen lokalen Webserver, öffnet einen Browser im Kiosk-Modus und zeigt Livestream, Uhrzeit, Wetter, Regenradar und optionale ÖPNV-Abfahrten.

## Raspberry Pi Start

Die lokale Konfiguration liegt unter `~/.config/BI-StorchCam/config.json`.

Autostart wird über das Script `scripts/install_linux_autostart.sh` eingerichtet. Der Kiosk-Start läuft über `scripts/start_pi5_touch.sh`.

```bash
cd ~/BI-StorchCam-work
bash scripts/install_linux_autostart.sh
bash scripts/start_pi5_touch.sh
```

Der Launcher überwacht den Chromium-Prozess. Falls der Kiosk-Browser abstürzt, wird er automatisch mit einer begrenzten Wiederanlaufverzögerung neu gestartet. Chromium-Ausgaben landen unter `~/.cache/BI-StorchCam/chromium.log`.

## Diagnose

```bash
cd ~/BI-StorchCam-work
bash scripts/storchcam_diagnose.sh
```

Weitere Einzeltests:

- Config testen: `python3 launcher.py --test-config`
- Nur Server starten: `python3 launcher.py --no-browser`
- Radar testen: `python3 launcher.py --test-radar`
- App-Log: `tail -n 200 ~/.cache/BI-StorchCam/storchcam.log`
- Chromium-Log: `tail -n 200 ~/.cache/BI-StorchCam/chromium.log`

## Hinweis

Lokale Pi-Konfigurationen gehören nicht ins Repository. Das Repository enthält nur Code, Defaults und Scripts.
