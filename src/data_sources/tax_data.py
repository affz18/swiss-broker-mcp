"""Schweizer Steuerfuss-Daten pro Gemeinde / Kanton.

Datenquelle: Eidgenoessische Steuerverwaltung (ESTV) bzw. kantonale
Open-Data-Portale. **Stichdatum: Steuerperiode 2025** (provisorische
Werte). Aenderungen bei Steuerfuessen erfolgen jaehrlich.

WICHTIG zur Interpretation:
Der `tax_multiplier` ist **nicht querkantonal vergleichbar**. Die
einzelnen Kantone benutzen unterschiedliche Bemessungssysteme:
- Mehrheit (z.B. ZH, BE, SG): Multiplikator des kantonalen Tarifs
  ("Steuerfuss in % des Einheitssatzes" → 1.19 = 119%).
- OW, NW, AR und andere: Einheitssatz-System mit anderer Skala.
- Stadtkantone (BS, GE): Steuerfuss meist tief (kein Gemeindesteuer-
  zuschlag).

Daher liefert dieses Modul ZUSAETZLICH `tax_rank_canton`, das
querkantonal vergleichbar ist (Quelle: ESTV Steuerbelastungsmonitor):
- "guenstig": ZG, OW, NW, SZ, AI
- "mittel":   ZH, BS, BL, AR, GR, GL, AG, SG, TG, LU, FR, VS, TI, SH, UR
- "teuer":    BE, GE, VD, JU, NE, SO

TODO (vor Public Release): Live-Anbindung an ESTV API
(steuerbelastung.estv.admin.ch) und/oder kantonale Open-Data-Portale
(z.B. statistik.zh.ch). Pro Gemeinde tagesaktuelle Werte.

Coverage MVP:
- 26 Kantone mit Mittelwert (`_KANTONAL_MEAN_TAX_MULTIPLIER`)
- Ausgewaehlte Gemeinden mit gemeindespezifischem Override
  (`_ZIP_TAX_MULTIPLIER_OVERRIDE`)
- Restliche Gemeinden bekommen den kantonalen Mittelwert + transparenten
  Hinweis im Output (`tax_multiplier_note`).
"""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

TaxRank = Literal["guenstig", "mittel", "teuer"]

TAX_DATA_STICHDATUM = "Steuerperiode 2025"

TAX_DATA_SOURCE_LABEL = (
    f"ESTV / kantonale Steuerverwaltungen, {TAX_DATA_STICHDATUM} "
    f"(provisorische Werte, kantonale Mittel + ausgewaehlte Gemeinden)"
)


# Kantonaler Mittelwert des kommunalen Steuerfuss-Multipliers fuer
# natuerliche Personen. Annaeherung 2025.
_KANTONAL_MEAN_TAX_MULTIPLIER: dict[str, float] = {
    "ZH": 1.19, "BE": 1.54, "LU": 1.81, "BS": 0.78, "BL": 0.68,
    "VD": 1.55, "GE": 0.475, "ZG": 0.59, "OW": 2.95, "NW": 2.66,
    "FR": 0.85, "VS": 1.40, "TI": 1.00, "SO": 1.18, "SH": 0.95,
    "AR": 4.00, "AI": 1.00, "SG": 1.45, "TG": 1.42, "GR": 0.95,
    "AG": 1.05, "JU": 2.00, "NE": 1.40, "UR": 1.00, "SZ": 1.50,
    "GL": 0.65,
}


# Gemeindespezifische Overrides (per ZIP). Wo wir konkrete Werte haben,
# ueberschreiben sie den kantonalen Mittelwert.
_ZIP_TAX_MULTIPLIER_OVERRIDE: dict[str, float] = {
    # Zuerich Stadt-Bezirke (alle gleicher Steuerfuss)
    "8001": 1.19,
    "8002": 1.19,
    "8004": 1.19,
    "8050": 1.19,
    "8400": 1.20,  # Winterthur
    # Bern
    "3000": 1.54,
    "3001": 1.54,
    "3011": 1.54,
    # Luzern
    "6000": 1.75,
    "6003": 1.75,
    "6004": 1.75,
    "6005": 1.75,
    # Basel (kein kommunaler Aufschlag im Stadtkanton)
    "4001": 0.78,
    "4051": 0.78,
    "4052": 0.78,
    "4410": 0.65,  # Liestal (BL)
    # Genf (kein kommunaler Aufschlag im Stadtkanton)
    "1200": 0.475,
    "1201": 0.475,
    "1202": 0.475,
    # Lausanne
    "1003": 0.79,
    "1005": 0.79,
    # Zug
    "6300": 0.55,
    "6330": 0.55,  # Cham
    # Innerschweiz - OW Sarnen (Beispiel aus Spec)
    "6060": 2.95,
    "6370": 2.66,  # Stans NW
    "6430": 1.50,  # Schwyz
    # St. Gallen
    "9000": 1.39,
    # Tessin
    "6900": 0.93,  # Lugano
    # Graubuenden
    "7000": 0.90,  # Chur
    # Wallis
    "1950": 1.40,  # Sion
    "3920": 1.20,  # Zermatt
}


# Kantonaler Steuer-Rang (querkantonal vergleichbar).
_TAX_RANK_BY_CANTON: dict[str, TaxRank] = {
    "ZG": "guenstig",
    "OW": "guenstig",
    "NW": "guenstig",
    "SZ": "guenstig",
    "AI": "guenstig",
    "ZH": "mittel",
    "BS": "mittel",
    "BL": "mittel",
    "AR": "mittel",
    "GR": "mittel",
    "GL": "mittel",
    "AG": "mittel",
    "SG": "mittel",
    "TG": "mittel",
    "LU": "mittel",
    "FR": "mittel",
    "VS": "mittel",
    "TI": "mittel",
    "SH": "mittel",
    "UR": "mittel",
    "BE": "teuer",
    "GE": "teuer",
    "VD": "teuer",
    "JU": "teuer",
    "NE": "teuer",
    "SO": "teuer",
}


class TaxInfo(TypedDict):
    """Steuer-Informationen fuer eine PLZ + Kanton."""

    multiplier: float
    rank_canton: TaxRank
    multiplier_note: str  # Erklaert ob gemeindespezifisch oder kantonal-Mittel
    stichdatum: str


class TaxDataNotCoveredError(ValueError):
    """PLZ + Kanton sind nicht in den Steuerdaten abgedeckt."""


def get_tax_info(zip_code: str, canton: str) -> TaxInfo:
    """Liefert Steuer-Multiplier + Rang fuer eine Schweizer PLZ.

    Args:
        zip_code: 4-stellige PLZ.
        canton: 2-Buchstaben Kantons-Code (z.B. "OW").

    Returns:
        TaxInfo mit multiplier (gemeindespezifisch wenn vorhanden,
        sonst kantonaler Mittelwert), rank_canton, multiplier_note
        (erklaert die Quelle des multiplier-Wertes) und stichdatum.

    Raises:
        TaxDataNotCoveredError: wenn weder PLZ-Override noch
            kantonaler Mittelwert vorhanden ist.
    """
    if zip_code in _ZIP_TAX_MULTIPLIER_OVERRIDE:
        multiplier = _ZIP_TAX_MULTIPLIER_OVERRIDE[zip_code]
        note = (
            "Gemeindespezifisch (Steuerperiode 2025). Achtung: Multiplier-"
            "Bedeutung variiert pro Kanton; siehe tax_rank_canton fuer "
            "querkantonalen Vergleich."
        )
    elif canton in _KANTONAL_MEAN_TAX_MULTIPLIER:
        multiplier = _KANTONAL_MEAN_TAX_MULTIPLIER[canton]
        note = (
            "Kantonaler Mittelwert (gemeindespezifischer Wert nicht in "
            "MVP-Tabelle). Fuer praezisere Werte direkt bei der "
            "Wohngemeinde anfragen."
        )
    else:
        raise TaxDataNotCoveredError(
            f"Weder PLZ {zip_code!r} noch Kanton {canton!r} in Steuerdaten."
        )

    if canton not in _TAX_RANK_BY_CANTON:
        raise TaxDataNotCoveredError(
            f"Kanton {canton!r} hat keinen tax_rank-Eintrag."
        )

    return TaxInfo(
        multiplier=multiplier,
        rank_canton=_TAX_RANK_BY_CANTON[canton],
        multiplier_note=note,
        stichdatum=TAX_DATA_STICHDATUM,
    )
