# BI-StorchCam Beta-Release-Checkliste

## Automatisierte Nachweise

- [ ] `ruff check .`
- [ ] `mypy bi_storchcam`
- [ ] `pytest -q`
- [ ] Playwright für 1024×600, 1280×720 und 1920×1080
- [ ] GitHub Actions unter Ubuntu und Windows, Python 3.10/3.12/3.13
- [ ] PyInstaller-Smoke-Test unter Linux x64 und Windows x64
- [ ] ARM64-Build lokal auf dem Raspberry Pi

## Funktionale Abnahme

- [ ] alle drei Startbefehle öffnen dieselbe Web-Kiosk-Anwendung
- [ ] Stream bleibt bei Wetter-, Radar-, Layout- und ÖPNV-Änderungen aktiv
- [ ] Streamstatus behauptet keine ungeprüfte Wiedergabe
- [ ] drei Sekunden lange Berührung und `Ctrl+Alt+S` öffnen den PIN-Dialog
- [ ] PIN liegt nicht im Klartext in Config, Logs oder Diagnose
- [ ] Haltestellen lassen sich hinzufügen, ändern, sortieren und löschen
- [ ] Linien-, Nachtbus-, Maximalzeilen- und Leeranzeigefilter wirken
- [ ] Radar zeigt Ort, Datenzeit, Quelle, Status und Attribution
- [ ] Windows zeigt keine erfundenen Nullwerte

## Raspberry-Pi-Hardwaretest

- [ ] `scripts/install_systemd_user.sh` aus beliebigem Repositorypfad funktioniert
- [ ] X11 beziehungsweise Wayland wird korrekt erkannt
- [ ] generisches Profil verändert weder Rotation noch Touchmatrix
- [ ] Browserabsturz löst begrenzten Wiederanlauf aus
- [ ] Python-Absturz wird von systemd neu gestartet
- [ ] Diagnosebericht enthält keine Geheimnisse
- [ ] mindestens acht Stunden mit `scripts/soak_test.py` stabil

## Veröffentlichung

- [ ] Status weiterhin als Beta ausweisen
- [ ] tatsächliche Zielgerät-Screenshots ergänzen
- [ ] bekannte Einschränkungen und getestete Commit-SHA dokumentieren
- [ ] keine ungeprüften Binärdateien hochladen
- [ ] GPL-3.0 sowie Datenquellen-Attribution beibehalten
