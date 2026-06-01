# API-Hinweise

## Wetter

Die Wetterdaten werden über Open-Meteo geladen.

## Geokodierung

Für Adresseingaben innerhalb von Bielefeld wird Nominatim/OpenStreetMap verwendet. Die App fragt nur beim Setup ab, nicht dauerhaft im Betrieb.

## Abfahrten

Die Abfahrten werden über den VRR-Haltestellenmonitor geladen.

Für Bielefeld/moBiel ist die bestätigte Haltestelle in der Konfiguration gespeichert. Im Betrieb wird nicht mehr gesucht, sondern direkt anhand der gespeicherten Station-ID geladen.

Beispiel:

```json
{
  "station_id": "23005489",
  "station_name": "Gellershagen Schneiderstraße"
}
```
