"""Schweizer PLZ -> Kanton + Gemeinde Lookup.

MVP-Strategie: embedded Tabelle der wichtigsten ~60 PLZ (Kantonshauptorte,
groesste Staedte, Tourismus-Hotspots, dein Sarnen-Beispiel 6060). Schluesse
ich aus, die nicht in der Tabelle sind, wirft `lookup_zip()` einen
`UnknownZipError` mit hilfreicher Fehlermeldung fuer den LLM.

TODO: Vor Public-Release auf vollstaendige PLZ-Tabelle wechseln. Quelle:
opendata.swiss "Amtliches Gemeindeverzeichnis" oder Schweizer Post
PLZ-Verzeichnis (~3000 Eintraege, ~150 KB JSON, problemlos in-memory).
"""

from __future__ import annotations

from typing_extensions import TypedDict


class ZipEntry(TypedDict):
    """Ergebnis eines PLZ-Lookups."""

    zip_code: str
    municipality: str
    canton: str  # 2-Buchstaben Code (ZH, OW, ...)
    canton_name: str  # vollstaendiger Kantonsname (deutsch)


class UnknownZipError(ValueError):
    """PLZ ist nicht in unserer Tabelle hinterlegt."""


CANTONS: dict[str, str] = {
    "AG": "Aargau",
    "AI": "Appenzell Innerrhoden",
    "AR": "Appenzell Ausserrhoden",
    "BE": "Bern",
    "BL": "Basel-Landschaft",
    "BS": "Basel-Stadt",
    "FR": "Freiburg",
    "GE": "Genf",
    "GL": "Glarus",
    "GR": "Graubuenden",
    "JU": "Jura",
    "LU": "Luzern",
    "NE": "Neuenburg",
    "NW": "Nidwalden",
    "OW": "Obwalden",
    "SG": "St. Gallen",
    "SH": "Schaffhausen",
    "SO": "Solothurn",
    "SZ": "Schwyz",
    "TG": "Thurgau",
    "TI": "Tessin",
    "UR": "Uri",
    "VD": "Waadt",
    "VS": "Wallis",
    "ZG": "Zug",
    "ZH": "Zuerich",
}


# PLZ -> (Gemeinde, Kantons-Code).
# Auswahl: Kantonshauptorte, groesste Staedte, Tourismus, Beispiel-PLZ aus
# der Spec. KEIN Anspruch auf Vollstaendigkeit - siehe TODO oben.
_ZIP_TABLE: dict[str, tuple[str, str]] = {
    # Zuerich
    "8000": ("Zuerich", "ZH"),
    "8001": ("Zuerich", "ZH"),
    "8002": ("Zuerich", "ZH"),
    "8004": ("Zuerich", "ZH"),
    "8050": ("Zuerich", "ZH"),
    "8400": ("Winterthur", "ZH"),
    # Bern
    "3000": ("Bern", "BE"),
    "3001": ("Bern", "BE"),
    "3011": ("Bern", "BE"),
    "2500": ("Biel/Bienne", "BE"),
    "3780": ("Gstaad", "BE"),
    # Luzern
    "6000": ("Luzern", "LU"),
    "6003": ("Luzern", "LU"),
    "6004": ("Luzern", "LU"),
    "6005": ("Luzern", "LU"),
    # Basel
    "4001": ("Basel", "BS"),
    "4051": ("Basel", "BS"),
    "4052": ("Basel", "BS"),
    "4410": ("Liestal", "BL"),
    # Genf
    "1200": ("Genf", "GE"),
    "1201": ("Genf", "GE"),
    "1202": ("Genf", "GE"),
    # Waadt
    "1003": ("Lausanne", "VD"),
    "1005": ("Lausanne", "VD"),
    "1820": ("Montreux", "VD"),
    "1860": ("Aigle", "VD"),
    # Zug
    "6300": ("Zug", "ZG"),
    "6330": ("Cham", "ZG"),
    # Innerschweiz
    "6060": ("Sarnen", "OW"),
    "6370": ("Stans", "NW"),
    "6430": ("Schwyz", "SZ"),
    "6440": ("Brunnen", "SZ"),
    "6460": ("Altdorf", "UR"),
    # Ostschweiz
    "9000": ("St. Gallen", "SG"),
    "9050": ("Appenzell", "AI"),
    "9100": ("Herisau", "AR"),
    "8200": ("Schaffhausen", "SH"),
    "8500": ("Frauenfeld", "TG"),
    "8750": ("Glarus", "GL"),
    # Aargau / Solothurn
    "5000": ("Aarau", "AG"),
    "5400": ("Baden", "AG"),
    "4500": ("Solothurn", "SO"),
    # Tessin
    "6500": ("Bellinzona", "TI"),
    "6600": ("Locarno", "TI"),
    "6900": ("Lugano", "TI"),
    # Graubuenden
    "7000": ("Chur", "GR"),
    "7500": ("St. Moritz", "GR"),
    "7270": ("Davos", "GR"),
    # Wallis
    "1950": ("Sion", "VS"),
    "3920": ("Zermatt", "VS"),
    "3900": ("Brig", "VS"),
    # Freiburg / Neuenburg / Jura
    "1700": ("Freiburg", "FR"),
    "2000": ("Neuenburg", "NE"),
    "2800": ("Delsberg", "JU"),
}


def lookup_zip(zip_code: str) -> ZipEntry:
    """Liefert Gemeinde + Kanton fuer eine Schweizer PLZ.

    Args:
        zip_code: 4-stellige PLZ als String (z.B. "6060").

    Returns:
        ZipEntry mit zip_code, municipality, canton (2-Buchstaben),
        canton_name (deutsch).

    Raises:
        UnknownZipError: wenn die PLZ nicht in der Tabelle ist. Die
            Fehlermeldung ist fuer LLM-Konsum optimiert (auf Deutsch,
            mit Hinweis auf Workaround).
    """
    zip_code = zip_code.strip()
    if zip_code not in _ZIP_TABLE:
        raise UnknownZipError(
            f"PLZ {zip_code!r} ist (noch) nicht in der Swiss-Broker-MCP "
            f"Tabelle hinterlegt. Aktuell sind ~60 wichtige Schweizer PLZ "
            f"abgedeckt (Kantonshauptorte, Grossstaedte, Tourismus). "
            f"Bitte mit einer anderen PLZ in der gleichen Region versuchen."
        )
    municipality, canton = _ZIP_TABLE[zip_code]
    return ZipEntry(
        zip_code=zip_code,
        municipality=municipality,
        canton=canton,
        canton_name=CANTONS[canton],
    )


def is_known_zip(zip_code: str) -> bool:
    """True wenn die PLZ in der Tabelle existiert."""
    return zip_code.strip() in _ZIP_TABLE
