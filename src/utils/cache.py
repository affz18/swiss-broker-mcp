"""In-Memory TTL Cache.

Einfacher dict-basierter Cache fuer HTTP-Responses externer APIs.
Default TTL: 3600s (1h) - BFS-Daten aendern sich quartalsweise.

Bewusst NICHT redis o.ae. - wir laufen auf einer Cloud Run Instanz,
kalter Start ist OK, und horizontale Skalierung ist fuer einen
Daten-Bridge-MCP nicht kritisch.

TODO: Implementation in Step 2.
"""
