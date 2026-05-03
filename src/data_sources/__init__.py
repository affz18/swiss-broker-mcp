"""Data Source Adapter - HTTP-Clients fuer externe Datenquellen.

Jeder Adapter:
- benutzt httpx (async)
- ist gecacht (utils/cache.py, TTL 1h)
- gibt strukturierte Python-Dicts/Dataclasses zurueck (NICHT roh-JSON)
- behandelt API-Fehler grace mit hilfreichen Messages
"""
