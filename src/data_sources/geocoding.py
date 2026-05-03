"""OpenStreetMap Nominatim Wrapper.

Endpoint: https://nominatim.openstreetmap.org/
Wichtig: User-Agent ist Pflicht (Usage Policy). Max 1 Request/Sekunde.

Funktionen (TODO):
- geocode_zip(zip_code: str) -> {lat, lon, municipality, canton}
- nearby_amenities(lat, lon, radius_m, kinds) -> list[Amenity]
"""
