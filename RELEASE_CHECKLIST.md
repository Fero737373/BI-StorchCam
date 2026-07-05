# BI-StorchCam Release-Checkliste

Diese Checkliste ist für einen ersten öffentlichen Preview-Release gedacht. Ziel ist ein sauberer Eindruck für Marketing, Konstruktion, interne Tester und spätere Nutzer.

## 1. Produktzustand

- [ ] Release als **Preview/Beta** kennzeichnen, nicht als fertiges Endprodukt.
- [ ] README beschreibt klar, dass BI-StorchCam ein Infoscreen für Livestream, Wetter, Regenradar und Abfahrten ist.
- [ ] Screenshots zeigen keine Debug-Ansicht und keine leeren Beispielkarten.
- [ ] Standardkonfiguration startet ohne manuelle Anpassung auf Windows und Linux/Raspberry Pi.

## 2. UI / Marketing-Eindruck

- [ ] Uhrzeit ist sofort lesbar.
- [ ] Wetterleiste ist kurz genug und zeigt keine komplette lange Adresse.
- [ ] Regenradar wirkt wie ein echtes Feature und nicht wie ein Platzhalter.
- [ ] Abfahrten werden nur angezeigt, wenn eine echte Haltestelle konfiguriert ist.
- [ ] Systemdaten sind im Standard ausgeblendet und nur für Diagnose aktivierbar.
- [ ] Menü ist verständlich für Nicht-IT-Nutzer.
- [ ] Haltestellensuche funktioniert ohne JSON-Bearbeitung.

## 3. Technik / Konstruktion

- [ ] Windows: `python launcher.py --test-config` läuft.
- [ ] Windows: `python launcher.py --test-radar` läuft oder zeigt sauberen Offline-Fehler.
- [ ] Windows: Browser startet mit Edge/Chrome automatisch.
- [ ] Linux/Raspberry: `python launcher.py --test-config` läuft.
- [ ] Linux/Raspberry: Chromium-Kiosk startet automatisch.
- [ ] Linux/Raspberry: Displayrotation und Touchmatrix funktionieren nur dort, wo sie gebraucht werden.
- [ ] Regenradar fällt bei Netzwerkfehlern sauber zurück.
- [ ] App läuft mindestens 2 Stunden ohne sichtbaren Fehler.

## 4. Release-Artefakte

- [ ] Windows-EXE bauen: `build_windows.bat`.
- [ ] Linux-Binary bauen: `./build_linux.sh`.
- [ ] Release-Notizen mit Preview-Hinweis schreiben.
- [ ] Screenshots für GitHub Release aktualisieren.
- [ ] Bekannte Einschränkungen dokumentieren.

## 5. Bekannte Einschränkungen für Preview

- YouTube-/Livestream-Embeds können je nach Quelle blockiert sein.
- Regenradar hängt von RainViewer und externen Kartenkacheln ab.
- Abfahrten hängen vom VRR-Haltestellenmonitor ab.
- Touch-/Rotationseinstellungen sind primär für Raspberry-Pi-Kiosk-Displays vorgesehen.
