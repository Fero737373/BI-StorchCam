# Provider- und API-Hinweise

## Lokale HTTP-API

- `GET /api/health`: Version, Uptime und State-Readiness
- `GET /api/state`: letzter In-Memory-Snapshot ohne neue Providerabfrage
- `GET /api/radar`: Radaranteil desselben Snapshots
- `GET /api/admin/status`: lokaler PIN-/Sessionstatus
- `POST /api/admin/setup`: einmaliges lokales PIN-Setup
- `POST /api/admin/login`: zeitlich begrenzte Admin-Session
- `GET /api/config`: validierte, redigierte Konfiguration; nach Setup authentifiziert
- `POST /api/config/save`: authentifizierter, größenbegrenzter Schreibzugriff
- `GET /api/station/search`: authentifizierte VRR-Suche

Fehler werden als JSON mit passenden HTTP-Statuscodes ausgegeben. Tracebacks werden nicht an den Browser übertragen.

## Externe Provider

- Open-Meteo: aktuelles Wetter und stündliche Zukunft ab der konfigurierten Zeitzone
- RainViewer: Messwert, optionaler Nowcast und Legacy-Fallback
- OpenStreetMap: Basiskartenkacheln mit sichtbarer Attribution
- VRR-Haltestellenmonitor: Suche und Abfahrten in der VRR-Region

Providerfehler bleiben im Snapshot sichtbar, beenden aber weder Server noch State-Worker.
