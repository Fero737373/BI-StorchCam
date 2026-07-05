# BI-StorchCam UI/UX Review 2026

## Zielbild

BI-StorchCam soll für einen Preview-Release wie ein modernes, ruhiges und professionelles Kiosk-/Dashboard-Produkt wirken. Der Screen muss auf Distanz lesbar sein, das Einstellungsmenü muss auch für Nicht-IT-Nutzer verständlich bleiben, und Diagnosefunktionen dürfen den öffentlichen Eindruck nicht dominieren.

## Größte UI-/UX-Probleme vor dem Refactor

1. **Kein klares Designsystem**  
   Farben, Abstände, Cards, Buttons und Formulare waren funktional, aber nicht als einheitliches System aufgebaut.

2. **Debug-Eindruck im Produkt-Screen**  
   Systemdaten, Beispielkarten und technische Labels konnten prominent erscheinen und den Release-Look schwächen.

3. **Menü wirkte wie Konfigurationsmaske**  
   Die Einstellungsoberfläche war nützlich, aber zu technisch und nicht ausreichend nach Nutzeraufgaben gruppiert.

4. **Uneinheitliche Zustände**  
   Lade-, Fehler-, Leer- und Erfolgszustände waren nicht konsistent visualisiert.

5. **Responsive und Accessibility nur teilweise abgedeckt**  
   Fokuszustände, Semantik, Skip-Link, Dialogrolle und mobile Layouts mussten verbessert werden.

## Umbauplan

1. UI-Struktur semantisch verbessern: Screen, Topbar, Feature-Cards, Settings-Dialog.
2. CSS als Designsystem neu aufbauen: Tokens, Komponenten, States, Responsive-Regeln.
3. Menü nach echten Aufgaben gruppieren: Bildschirm, Anzeige, Abfahrten.
4. Interaktion verbessern: Toasts, Statusmeldungen, Suchzustände, Tastatur-Escape, Fokusführung.
5. Alte Configs migrieren, damit alte Debug-Werte den Release-Screen nicht zerstören.
6. Keine Business-Logik verändern; bestehende Endpunkte und IDs bleiben kompatibel.

## Ergebnis

- Moderneres SaaS-/Dashboard-artiges Erscheinungsbild.
- Ruhigere visuelle Hierarchie.
- Bessere Lesbarkeit und klarere Cards.
- Professionellere Settings-Oberfläche.
- Einheitliche Buttons, Inputs, Toggles und Statusmeldungen.
- Verbesserte Tastaturbedienung und Fokuszustände.
- Saubere leere/fehlerhafte Zustände für Haltestellensuche und Radar.

## Release-Hinweis

Der Stand ist weiterhin als **Preview/Beta** zu kommunizieren. Die UI ist für eine erste öffentliche oder interne Release-Abnahme vorbereitet, aber noch nicht als finales 1.0-Produkt zu verkaufen.
