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

Fehler werden als JSON mit passenden HTTP-Statuscodes ausgegeben. Tracebacks werden nicht an den Browser übertragen.

## Externe Provider

- Open-Meteo: aktuelles Wetter und stündliche Zukunft ab der konfigurierten Zeitzone
- Nominatim (OpenStreetMap): Adress- und Ortssuche, Rückfall auf Open-Meteo-Geocoding
- YouTube: Live-Suche über die öffentliche Suchseite oder optional die Data API v3
- VRR-Haltestellenmonitor: Suche und Abfahrten in der VRR-Region

Providerfehler bleiben im Snapshot sichtbar, beenden aber weder Server noch State-Worker.
