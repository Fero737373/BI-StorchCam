# Architektur

BI-StorchCam besitzt genau einen Produktpfad:

1. `kiosk_app.main` lädt und validiert die lokale Konfiguration.
2. `StateManager` aktualisiert Wetter, VRR und optionale Systemdaten nach getrennten Intervallen.
3. `StorchServer` bindet den konfigurierten Port und liefert nur unveränderliche State-Snapshots an `/api/state`.
4. Der Hauptprozess wartet auf `/api/health` mit `state_ready=true`.
5. Erst danach startet `BrowserManager` einen Chromium-Familienprozess.
6. Docker (`restart: unless-stopped`, Healthcheck auf `/api/health`) überwacht den Python-Prozess. `BrowserManager` überwacht den Chromium-Prozess im Container, der über den Wayland-Socket des Hosts auf dem Bildschirm erscheint.

Die API lädt keine externen Provider pro Request. Configänderungen invalidieren den Zeitplan des State-Managers. Schreibzugriffe erfordern ein kurzlebiges In-Memory-Token. Die PIN liegt nur als PBKDF2-Hash in der lokalen Config.

Provider bleiben hinter serialisierbaren Ergebnissen gekapselt. Neue Anbieter müssen die bestehende Configvalidierung, einen klaren Providernamen und einen Fetchpfad ergänzen; UI und HTTP-State benötigen dadurch keinen grundlegenden Umbau.
