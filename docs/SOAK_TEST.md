# Raspberry-Pi-Soak-Test

Ein bestandener Hardwaretest darf erst nach realer Ausführung dokumentiert werden. Ziel sind mindestens acht Stunden.

## Vorbereitung

```bash
cd /pfad/zu/BI-StorchCam
source .venv/bin/activate
pytest -q
bash scripts/install_systemd_user.sh
```

Ermittle anschließend die Browser-PID aus `bash scripts/diagnose.sh` und starte den Monitor:

```bash
python scripts/soak_test.py --hours 8 --browser-pid PID --simulate-browser-crash-after 300
```

Das Script prüft Healthcheck, State-Zeitstempel, Speicherentwicklung, Loggrößen und nach dem gezielten Browser-SIGTERM den erneuten Browserstart. Ein Provider-Offlinezustand darf im State erscheinen, der Healthcheck muss jedoch erreichbar bleiben. Die automatisierten Provider-Fehlertests ergänzen diese Hardwareprüfung ohne echte APIs.

## Erwartetes Ergebnis

- `/api/health` bleibt erreichbar und `state_ready` bleibt wahr.
- `generated_at` wird weiter aktualisiert.
- Der Python-RSS wächst nicht kontinuierlich unbeschränkt.
- `storchcam.log` und `chromium.log` überschreiten ihre konfigurierte Rotation nicht dauerhaft.
- Der explizit beendete Browser startet nach begrenztem Backoff neu.
- Wetter-, Radar- oder VRR-Fehler beenden den Prozess nicht.

Bewahre den erzeugten Bericht aus `~/.cache/BI-StorchCam/soak-*.json` gemeinsam mit der getesteten Commit-SHA auf.
