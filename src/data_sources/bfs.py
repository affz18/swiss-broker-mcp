"""Bundesamt fuer Statistik (BFS) - embedded Preis-/Trend-Tabellen (MVP).

Liefert Basis-Preise pro m2 und Year-over-Year-Trends pro Kanton +
Property-Type. Die Werte sind plausible Annaeherungen an oeffentlich
publizierte BFS-Indikatoren (Wohnimmobilienpreisindex, regionale
Mittelwerte). Sie sollen das LLM mit GROSSORDNUNGSRICHTIGEN Daten
versorgen, sind aber KEIN Ersatz fuer eine professionelle Bewertung.

TODO (vor Public Release): Live-Anbindung an BFS pxweb-API
(https://www.pxweb.bfs.admin.ch/) oder opendata.swiss CKAN-Datasets,
sodass die Werte automatisch quartalsweise aktualisieren. Dieses Modul
behaelt dann das gleiche Interface, ersetzt die _BASE_PRICE_PER_M2_CHF
und _YOY_CHANGE_PERCENT Konstanten durch gecachte API-Calls.
"""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

PropertyType = Literal["apartment", "house", "land"]

# Datenquellen-Label, das im Tool-Output mitgeliefert wird (Transparenz).
DATA_SOURCE_LABEL = (
    "BFS Wohnimmobilienpreisindex 2024 (regionale Annaeherung, "
    "kantonsweise Mittelwerte)"
)


class CantonPrices(TypedDict):
    """Mittlerer Verkaufspreis pro m2 Wohnflaeche in CHF."""

    apartment: int  # Eigentumswohnung (Stockwerkeigentum)
    house: int  # Einfamilienhaus
    land: int  # Bauland


# Plausible kantonale Mittelwerte 2024 (CHF pro m2).
# Apartments / Houses: Wohnflaeche. Land: Grundstueck.
# WICHTIG: Annaeherungen, nicht offizielle BFS-Zahlen 1:1.
_BASE_PRICE_PER_M2_CHF: dict[str, CantonPrices] = {
    "ZH": {"apartment": 12500, "house": 11000, "land": 1800},
    "GE": {"apartment": 13500, "house": 12000, "land": 2200},
    "ZG": {"apartment": 14000, "house": 12500, "land": 2500},
    "BS": {"apartment": 9800, "house": 9000, "land": 1500},
    "BL": {"apartment": 9000, "house": 8000, "land": 1100},
    "VD": {"apartment": 11500, "house": 10000, "land": 1600},
    "BE": {"apartment": 7500, "house": 6800, "land": 700},
    "LU": {"apartment": 10000, "house": 8800, "land": 1200},
    "SZ": {"apartment": 10500, "house": 9500, "land": 1300},
    "NW": {"apartment": 9500, "house": 8500, "land": 1100},
    "OW": {"apartment": 7500, "house": 6800, "land": 700},
    "UR": {"apartment": 6500, "house": 5800, "land": 500},
    "GR": {"apartment": 10000, "house": 8500, "land": 900},
    "TI": {"apartment": 8500, "house": 7500, "land": 800},
    "VS": {"apartment": 7500, "house": 6500, "land": 700},
    "FR": {"apartment": 8000, "house": 7000, "land": 800},
    "NE": {"apartment": 6500, "house": 5800, "land": 500},
    "JU": {"apartment": 5000, "house": 4500, "land": 300},
    "SO": {"apartment": 7000, "house": 6300, "land": 600},
    "AG": {"apartment": 9000, "house": 7800, "land": 900},
    "SG": {"apartment": 7500, "house": 6800, "land": 700},
    "TG": {"apartment": 7000, "house": 6200, "land": 600},
    "SH": {"apartment": 6500, "house": 5800, "land": 500},
    "AR": {"apartment": 6000, "house": 5300, "land": 400},
    "AI": {"apartment": 6000, "house": 5300, "land": 400},
    "GL": {"apartment": 5500, "house": 5000, "land": 400},
}


# Year-over-Year Veraenderung der Preise in Prozent (Q4 2024 vs Q4 2023).
# Plausible Approximation des BFS Wohnimmobilienpreisindex.
_YOY_CHANGE_PERCENT: dict[str, float] = {
    "ZH": 4.5, "GE": 3.8, "ZG": 5.2, "BS": 2.1, "BL": 2.5,
    "VD": 4.0, "BE": 2.5, "LU": 4.2, "SZ": 4.8, "NW": 4.0,
    "OW": 4.2, "UR": 1.5, "GR": 5.0, "TI": 2.0, "VS": 3.5,
    "FR": 3.0, "NE": 1.5, "JU": 0.5, "SO": 2.0, "AG": 3.5,
    "SG": 2.8, "TG": 3.0, "SH": 1.8, "AR": 1.5, "AI": 1.2,
    "GL": 1.0,
}


# Leerstandsquote Wohnungen pro Kanton in Prozent (BFS jaehrlich).
# Plausible Approximation 2024. Schweizer Schnitt liegt bei ~1.0%.
# Niedrige Werte = enger Markt = relevant fuer Buyer-Akquise.
_VACANCY_RATE_PERCENT: dict[str, float] = {
    "ZH": 0.7, "GE": 0.5, "ZG": 0.6, "BS": 1.0, "BL": 1.2,
    "VD": 0.8, "BE": 1.5, "LU": 1.2, "SZ": 1.0, "NW": 0.9,
    "OW": 0.8, "UR": 1.5, "GR": 1.0, "TI": 1.5, "VS": 2.0,
    "FR": 1.2, "NE": 2.5, "JU": 3.0, "SO": 2.0, "AG": 1.8,
    "SG": 2.0, "TG": 1.8, "SH": 1.5, "AR": 1.8, "AI": 1.5,
    "GL": 2.5,
}

# Schweiz-weiter Mittelwert (Fallback fuer unbekannte Kantone /
# unbekannte PLZ in Tools, die "graceful fallback" machen).
NATIONAL_YOY_CHANGE_PERCENT = 3.0
NATIONAL_VACANCY_RATE_PERCENT = 1.1


class CantonNotCoveredError(ValueError):
    """Kanton ist nicht in der BFS-Tabelle hinterlegt."""


def get_base_price_per_m2(canton: str, property_type: PropertyType) -> int:
    """Mittlerer Verkaufspreis CHF/m2 fuer einen Kanton + Immobilientyp.

    Args:
        canton: 2-Buchstaben Kantons-Code (z.B. "OW", "ZH").
        property_type: "apartment" | "house" | "land".

    Returns:
        Preis in CHF pro m2 (gerundet).

    Raises:
        CantonNotCoveredError: wenn der Kanton nicht in der Tabelle ist.
    """
    if canton not in _BASE_PRICE_PER_M2_CHF:
        raise CantonNotCoveredError(
            f"Kanton {canton!r} ist nicht in der BFS-Tabelle. "
            f"Bekannte Kantone: {sorted(_BASE_PRICE_PER_M2_CHF.keys())}."
        )
    return _BASE_PRICE_PER_M2_CHF[canton][property_type]


def get_yoy_change_percent(canton: str) -> float:
    """Year-over-Year Preisveraenderung in Prozent fuer einen Kanton.

    Positiver Wert = Preise gestiegen. Default 0.0 bei unbekanntem Kanton.
    """
    return _YOY_CHANGE_PERCENT.get(canton, 0.0)


def get_vacancy_rate_percent(canton: str) -> float:
    """Wohnungs-Leerstandsquote in Prozent fuer einen Kanton.

    Niedriger Wert = enger Markt. Default = nationaler Mittelwert
    bei unbekanntem Kanton (Fallback fuer Tools mit graceful fallback).
    """
    return _VACANCY_RATE_PERCENT.get(canton, NATIONAL_VACANCY_RATE_PERCENT)


def covered_cantons() -> list[str]:
    """Liste aller Kantone, fuer die wir Preisdaten haben."""
    return sorted(_BASE_PRICE_PER_M2_CHF.keys())
