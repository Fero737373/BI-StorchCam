# Livestream-first Redesign

## Ziel

BI-StorchCam ist in erster Linie ein Livestream-Viewer. Uhrzeit, Wetter, Regenradar und ÖPNV-Abfahrten sind Zusatzinformationen. Sie dürfen den Stream nicht dominieren, sondern sollen ihn ergänzen.

## Produkt-Fokus

Der Benutzer soll auf einem Raspberry-Pi-Display, Büro-Monitor oder normalen Desktop zuerst den Livestream sehen. Die Zusatzmodule müssen wie ein professionelles Overlay wirken: lesbar, ruhig, adaptiv und nicht wie separate Test-Cards.

## Pflichtmodule

- Livestream als Hauptfläche
- Uhrzeit
- Wetter
- Regenradar
- ÖPNV-Abfahrten
- Konfiguration über Menü
- Autostart auf Raspberry Pi

## Layout-Prinzip

Der Stream ist immer die visuelle Basis. Add-ons liegen als dezente, dunkle Overlays darüber.

- 7-Zoll Pi: kompakte Overlays, wenig Flächenverbrauch, große Lesbarkeit
- Desktop/Monitor: größere Overlays, bessere Abstände, aber Stream bleibt Hauptinhalt
- keine weißen ÖPNV-Cards
- kein Radar unter der Uhr
- keine riesigen dunklen Leerräume als Hauptdesign
- keine Systemdaten im normalen Produktmodus

## Responsive Verhalten

Das Layout muss sich automatisch anpassen:

- kleine Displays: kompakte Topbar plus untere Infoleiste
- mittlere Displays: Radar links unten, Abfahrten rechts unten, Uhr oben links
- große Displays: mehr Abstand und größere Schrift, aber gleiche Hierarchie

## Nächster Umsetzungsschritt

Nicht weiter am bestehenden CSS herumflicken. Stattdessen Web-Frontend strukturell neu aufsetzen:

1. HTML-Screenstruktur für Stream-first Layout vereinfachen
2. CSS neu als responsive Overlay-System schreiben
3. JavaScript nur an neue IDs/Klassen anpassen, Logik erhalten
4. Pi-Autostart behalten
5. lokale Raspberry-Pi-Konfiguration nicht ins Repository übernehmen

## Arbeitsregel

Jede größere Änderung erfolgt auf einem eigenen Branch. Main wird erst aktualisiert, wenn die Änderung visuell geprüft ist.
