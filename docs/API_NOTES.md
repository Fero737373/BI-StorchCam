# Provider- und API-Hinweise

## Lokale HTTP-API

- `GET /api/health`: Version, Uptime und State-Readiness
- `GET /api/state`: letzter In-Memory-Snapshot ohne neue Providerabfrage
- `GET /api/admin/status`: lokaler PIN-/Sessionstatus
- `POST /api/admin/setup`: einmaliges lokales PIN-Setup
- `POST /api/admin/login`: zeitlich begrenzte Admin-Session
- `GET /api/config`: validierte, redigierte Konfiguration; nach Setup authentifiziert
- `POST /api/config/save`: authentifizierter, größenbegrenzter Schreibzugriff
- `GET /api/station/search`: authentifizierte VRR-Suche
- `GET /api/live/search?q=`: Live-Streams auf YouTube
- `GET /api/location/search?q=`: Adress- und Ortssuche weltweit
- `GET /api/location/timezone?lat=&lon=`: Zeitzone zu Koordinaten
- `POST /api/music/spotify/authorize` (Admin): startet die Spotify-Anmeldung (Authorization Code mit PKCE) und liefert die Login-Adresse
- `GET /api/music/spotify/callback`: Rücksprung von Spotify, geschützt über den einmaligen `state`; leitet auf `/?music=connected` bzw. `/?music=error` um
- `POST /api/music/spotify/disconnect` (Admin): löscht den gespeicherten Spotify-Zugang
- `POST /api/music/ytmusic/login` (Admin): öffnet auf dem angeschlossenen Bildschirm ein Chromium-Fenster mit der Google-Anmeldung für YouTube Music
- `GET /api/music/ytmusic/login` (Admin): Stand der Anmeldung (`idle`, `pending`, `connected`, `error`)
- `POST /api/music/ytmusic/cancel` (Admin): schließt das Anmeldefenster
- `POST /api/music/ytmusic/disconnect` (Admin): löscht den gespeicherten YouTube-Music-Zugang
- `POST /api/player/search` (Admin): `{service: "ytmusic"|"spotify", query}` → Treffer mit `kind`, `id`, `title`, `subtitle`, `cover`
- `POST /api/player/playlists` (Admin): `{service}` → eigene Playlists (YouTube-Music-Bibliothek inkl. „Liked Music“ bzw. Spotify `/me/playlists`), Format wie bei der Suche
- `POST /api/player/play` (Admin): `{service, kind, id}` startet die Wiedergabe auf dem Pi; es spielt immer nur ein Dienst
- `POST /api/player/control` (Admin; vom Pi selbst auch ohne Anmeldung für die Knöpfe der Songkarte): `{target: "pi"|"spotify", action: "toggle"|"next"|"previous"|"stop"|"volume", value}`
- `GET /api/music/spotify/pair`, `POST /api/music/spotify/pair`, `POST /api/music/spotify/unpair` (Admin): Pi als Spotify-Lautsprecher koppeln (Kopplungsadresse und QR-Code) bzw. die Kopplung löschen
- `GET /api/bluetooth` (Admin): Adapter, Audiogeräte und laufende Aktion; ohne Adapter `available: false` mit Fehlertext
- `POST /api/bluetooth/scan`, `/connect`, `/disconnect`, `/remove` (Admin): `{mac}`; laufen im Hintergrund, der Fortschritt steht in `GET /api/bluetooth`

Fehler werden als JSON mit passenden HTTP-Statuscodes ausgegeben. Tracebacks werden nicht an den Browser übertragen.

## Externe Provider

- Open-Meteo: aktuelles Wetter und stündliche Zukunft ab der konfigurierten Zeitzone
- Nominatim (OpenStreetMap): Adress- und Ortssuche, Rückfall auf Open-Meteo-Geocoding
- YouTube: Live-Suche über die öffentliche Suchseite oder optional die Data API v3
- VRR-Haltestellenmonitor: Suche und Abfahrten in der VRR-Region
- Spotify Web API: aktueller Song (`/me/player/currently-playing`), Suche, Wiedergabe und Steuerung (`/me/player/...`); der Refresh-Token liegt in `spotify_token.json` neben der `config.json` (Dateirechte 600). Für Steuerung und eigene Playlists braucht die Verbindung die Rechte `user-read-playback-state`, `user-modify-playback-state`, `playlist-read-private` und `playlist-read-collaborative`; ältere Verbindungen im Menü einmal neu verbinden
- Spotify auf dem Pi: librespot 0.8 (aus raspotify 0.48.3) läuft als Spotify-Connect-Lautsprecher „StorchCam“ mit PulseAudio-Ausgabe. Gekoppelt wird per Gerätecode (`--enable-device-auth`, Adresse spotify.com/pair); die Zugangsdaten liegen in `librespot/` neben der `config.json`. Abgespielt wird über die Web API mit `device_id` dieses Lautsprechers
- YouTube Music auf dem Pi: mpv (JSON-IPC) spielt die Audio-Streams, die yt-dlp mit den YouTube-Music-Cookies auflöst; yt-dlp braucht dafür die JavaScript-Laufzeit Deno. Ein Song startet das passende Radio, Alben und Playlists laufen als Warteschlange
- Bluetooth: `bluetoothctl` spricht über den eingebundenen System-D-Bus (`/run/dbus/system_bus_socket`) mit BlueZ auf dem Host. PipeWire auf dem Host nimmt einen verbundenen Lautsprecher selbst als Ausgabe. Weil PipeWire Bluetooth-Lautsprecher oft mit 40 % (rund -24 dB) startet, stellt die App die Ausgabe nach dem Verbinden und bei jedem Abspielen per `pactl` auf 100 %; leiser gestellt wird im Player
- YouTube Music (inoffizielle Bibliothek ytmusicapi): Google sperrt die Geräteanmeldung (OAuth) für YouTube Music seit 2025 und verweigert Anmeldungen in ferngesteuerten Browsern. Deshalb öffnet die App ein gewöhnliches Chromium-Fenster ohne Debug-Zugang (Profil `ytmusic-browser/` neben der `config.json`) mit der normalen Google-Anmeldung. Sie erkennt die Anmeldung am Namen des Sitzungscookies in der Cookie-Datenbank, schließt das Fenster und liest die youtube.com-Cookies danach mit einem Headless-Chromium über `--remote-debugging-pipe` aus. Die Cookies liegen in `ytmusic_auth.json` (Dateirechte 600). Das Profil bleibt bis „YouTube Music trennen“ erhalten, sodass eine erneute Anmeldung meist ohne Passwort durchläuft. Es gibt keine „läuft gerade“-Schnittstelle: Der neueste Eintrag im Wiedergabeverlauf gilt ab seinem Erscheinen für seine Länge plus 30 s als laufend. Pause wird nicht erkannt, und der erste Song nach einem Neustart wird nicht angezeigt

Providerfehler bleiben im Snapshot sichtbar, beenden aber weder Server noch State-Worker.
