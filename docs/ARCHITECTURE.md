# Architektur

BI-StorchCam besitzt genau einen Produktpfad:

1. `kiosk_app.main` lädt und validiert die lokale Konfiguration.
2. `StateManager` aktualisiert Wetter, VRR, DWD-Warnungen, Musik und optionale Systemdaten nach getrennten Intervallen und führt je Quelle einen Zustand (`health`) für die Übersicht im Menü.
3. `StorchServer` bindet den konfigurierten Port und liefert nur unveränderliche State-Snapshots an `/api/state`.
4. Der Hauptprozess wartet auf `/api/health` mit `state_ready=true`.
5. Erst danach startet `BrowserManager` einen Chromium-Familienprozess.
6. Docker (`restart: unless-stopped`, Healthcheck auf `/api/health`) überwacht den Python-Prozess. `BrowserManager` überwacht den Chromium-Prozess im Container, der über den Wayland-Socket des Hosts auf dem Bildschirm erscheint.

Der Livestream läuft im eigenen Player: `/api/stream/source` löst YouTube per yt-dlp in eine HLS-Playlist (Livestream) oder eine einzelne Videodatei (normales Video) auf, `hls_proxy` reicht Playlist, Segmente und Videodateien signiert über den lokalen Server durch, hls.js bzw. das video-Element spielen sie ab. Chromium läuft mit Schaltern, die Medien im Hintergrund oder unter anderen Fenstern nicht anhalten. Fällt eine Kamera aus, wechselt die Oberfläche selbst zum nächsten Favoriten und prüft alle paar Minuten, ob die eigentliche Kamera wieder läuft.

Die Oberfläche (`web/index.html`, `app.js`, `style.css`) ist eine einzige Seite ohne Build-Schritt: Kiosk mit Infoleiste, Kompaktleiste, Detailansichten und Nachtmodus, darüber das Menü als Seitenpanel. Jede Einstellung speichert sofort über `/api/config/save` (mit Rückgängig), Themes sind reine CSS-Variablen auf `body[data-theme]`. Die strenge CSP (`'self'`, keine Inline-Styles) bleibt erhalten: Farben kommen über Klassen und SVG-Attribute, Bewegungen über die Web Animations API.

Musik auf dem Pi läuft über ein einziges mpv im Leerlauf (`player.py`): YouTube Music als Warteschlange, Radio als Senderadresse mit ICY-Titel. `listening.py` führt den Verlauf („Weiterhören“) und den Ausschalt-Timer. `pairing.py` vergibt den Kopplungscode fürs Handy; Geräte im Heimnetz bekommen nur damit oder mit PIN eine Sitzung.

Die API lädt außer der Streamauflösung keine externen Provider pro Request. Configänderungen invalidieren den Zeitplan des State-Managers. Schreibzugriffe erfordern ein kurzlebiges In-Memory-Token. Die PIN liegt nur als PBKDF2-Hash in der lokalen Config.

Provider bleiben hinter serialisierbaren Ergebnissen gekapselt. Neue Anbieter müssen die bestehende Configvalidierung, einen klaren Providernamen und einen Fetchpfad ergänzen; UI und HTTP-State benötigen dadurch keinen grundlegenden Umbau.
