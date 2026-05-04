"""Schweizer PLZ -> Kanton + Gemeinde Lookup.

Vollstaendige Tabelle aller Schweizer PLZ (~3362 Eintraege, 26 Kantone),
embedded als JSON-Resource (`swiss_zip_data.json`, ~96 KB).

Datenquelle: `zauberware/postal-codes-json-xml-csv` (Mirror von
geonames.org). Reproduzierbar via `scripts/build_zip_table.py`.

Konventionen:
- Gemeindenamen sind in der jeweiligen offiziellen Sprache der Gemeinde
  ("Geneve", "Lausanne", "Locarno", "Sarnen") - so wie sie auf der
  Gemeindewebseite stehen. Kantonsnamen sind in unserer CANTONS-Map
  immer auf Deutsch (z.B. "GE" -> "Genf" auch wenn Stadt "Geneve").
- ASCII-only: Umlaute werden zu ae/oe/ue transliteriert (Konvention
  fuer den gesamten Codebase). Der LLM-Client kann beim Output an den
  Endnutzer wieder Umlaute setzen.
- Bei PLZ die mehrere Gemeinden ueberspannen (~221 von 3362) waehlt
  der Build-Script die kanonische Gemeinde (Ortsname == Gemeindename).
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Final

from typing_extensions import TypedDict


class ZipEntry(TypedDict):
    """Ergebnis eines PLZ-Lookups."""

    zip_code: str
    municipality: str
    canton: str  # 2-Buchstaben Code (ZH, OW, ...)
    canton_name: str  # vollstaendiger Kantonsname (deutsch)


class UnknownZipError(ValueError):
    """PLZ ist nicht im Schweizer PLZ-Register."""


CANTONS: Final[dict[str, str]] = {
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


def _load_zip_table() -> dict[str, tuple[str, str]]:
    """JSON-Resource laden und in dict konvertieren."""
    raw_text = resources.files("src.utils").joinpath("swiss_zip_data.json").read_text(
        encoding="utf-8"
    )
    raw: dict[str, list[str]] = json.loads(raw_text)
    return {zip_code: (entry[0], entry[1]) for zip_code, entry in raw.items()}


# Vollstaendige Tabelle aller Schweizer PLZ - geladen einmal beim Import.
_ZIP_TABLE: Final[dict[str, tuple[str, str]]] = _load_zip_table()


def lookup_zip(zip_code: str) -> ZipEntry:
    """Liefert Gemeinde + Kanton fuer eine Schweizer PLZ.

    Args:
        zip_code: 4-stellige PLZ als String (z.B. "6060").

    Returns:
        ZipEntry mit zip_code, municipality, canton (2-Buchstaben),
        canton_name (deutsch).

    Raises:
        UnknownZipError: wenn die PLZ nicht im Schweizer PLZ-Register
            existiert. Die Fehlermeldung ist fuer LLM-Konsum optimiert.
    """
    zip_code = zip_code.strip()
    if zip_code not in _ZIP_TABLE:
        raise UnknownZipError(
            f"PLZ {zip_code!r} existiert nicht im Schweizer PLZ-Register. "
            f"Bitte die 4-stellige Postleitzahl pruefen."
        )
    municipality, canton = _ZIP_TABLE[zip_code]
    return ZipEntry(
        zip_code=zip_code,
        municipality=municipality,
        canton=canton,
        canton_name=CANTONS[canton],
    )


def is_known_zip(zip_code: str) -> bool:
    """True wenn die PLZ im Schweizer PLZ-Register existiert."""
    return zip_code.strip() in _ZIP_TABLE


def total_zip_count() -> int:
    """Anzahl PLZ in der Tabelle - fuer Doku/Health-Output."""
    return len(_ZIP_TABLE)
