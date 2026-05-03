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


# --- Demografische + Miet-Daten fuer get_neighborhood_profile ---
#
# Quellen-Approximationen (Stichdatum 2024):
# - Population: BFS STATPOP (Staendige Wohnbevoelkerung 31.12.2023)
# - Mieten: BFS Mietpreisstrukturerhebung
# - Avg Age: BFS Altersstruktur Bevoelkerung
# - Avg Household Size: BFS Haushaltsgroessen
# - Median Income: BFS HABE / Steuerstatistik (Brutto-Einkommen Haushalt)
DEMOGRAPHICS_SOURCE_LABEL = (
    "BFS STATPOP / Mietpreisstrukturerhebung / HABE 2024 (Annaeherungen, "
    "kantonale Mittelwerte; Population pro Gemeinde)"
)


# Population pro Gemeinde (Stichdatum 2024, gerundet).
# Schluessel ist der Gemeindename wie in swiss_zip._ZIP_TABLE.
_POPULATION_BY_MUNICIPALITY: dict[str, int] = {
    "Zuerich": 430_000,
    "Winterthur": 117_000,
    "Bern": 134_000,
    "Biel/Bienne": 56_000,
    "Gstaad": 7_000,  # Saanen
    "Luzern": 83_000,
    "Basel": 173_000,
    "Liestal": 14_000,
    "Genf": 203_000,
    "Lausanne": 142_000,
    "Montreux": 26_000,
    "Aigle": 11_000,
    "Zug": 31_000,
    "Cham": 17_000,
    "Sarnen": 10_300,
    "Stans": 8_500,
    "Schwyz": 15_500,
    "Brunnen": 9_000,  # Ingenbohl
    "Altdorf": 9_500,
    "St. Gallen": 76_000,
    "Appenzell": 6_000,
    "Herisau": 16_000,
    "Schaffhausen": 36_000,
    "Frauenfeld": 26_000,
    "Glarus": 12_500,
    "Aarau": 22_000,
    "Baden": 20_000,
    "Solothurn": 17_000,
    "Bellinzona": 44_000,
    "Locarno": 16_500,
    "Lugano": 63_000,
    "Chur": 36_000,
    "St. Moritz": 5_000,
    "Davos": 11_000,
    "Sion": 35_000,
    "Zermatt": 5_500,
    "Brig": 13_500,
    "Freiburg": 38_000,
    "Neuenburg": 33_000,
    "Delsberg": 13_000,
}


# Median-Mietpreis CHF pro m2 pro Monat (Wohnungen, Bestand + Neu),
# kantonsweise. Quelle: BFS Mietpreisstrukturerhebung 2024 (Annaeherung).
_MEDIAN_RENT_CHF_PER_M2: dict[str, float] = {
    "ZH": 20.50, "GE": 22.00, "ZG": 22.50, "BS": 17.00, "BL": 16.00,
    "VD": 18.00, "BE": 14.50, "LU": 17.00, "SZ": 18.00, "NW": 17.00,
    "OW": 16.00, "UR": 13.50, "GR": 16.00, "TI": 14.50, "VS": 14.00,
    "FR": 15.00, "NE": 13.00, "JU": 11.50, "SO": 13.50, "AG": 15.50,
    "SG": 14.50, "TG": 13.50, "SH": 13.50, "AR": 12.50, "AI": 12.50,
    "GL": 12.00,
}

# Durchschnittsalter pro Kanton (BFS 2024, Annaeherung).
_AVG_AGE: dict[str, float] = {
    "ZH": 41.5, "GE": 41.0, "ZG": 41.5, "BS": 42.5, "BL": 43.5,
    "VD": 41.5, "BE": 43.5, "LU": 42.0, "SZ": 42.5, "NW": 43.0,
    "OW": 42.0, "UR": 43.5, "GR": 44.0, "TI": 45.5, "VS": 43.5,
    "FR": 41.0, "NE": 43.0, "JU": 43.5, "SO": 43.0, "AG": 42.5,
    "SG": 42.5, "TG": 42.5, "SH": 44.0, "AR": 44.5, "AI": 41.0,
    "GL": 43.0,
}

# Durchschnittliche Haushaltsgroesse (Personen) pro Kanton, Annaeherung 2024.
_AVG_HOUSEHOLD_SIZE: dict[str, float] = {
    "ZH": 2.1, "GE": 2.2, "ZG": 2.3, "BS": 1.9, "BL": 2.2,
    "VD": 2.2, "BE": 2.1, "LU": 2.3, "SZ": 2.4, "NW": 2.4,
    "OW": 2.4, "UR": 2.3, "GR": 2.1, "TI": 2.2, "VS": 2.3,
    "FR": 2.4, "NE": 2.1, "JU": 2.2, "SO": 2.2, "AG": 2.3,
    "SG": 2.3, "TG": 2.3, "SH": 2.1, "AR": 2.3, "AI": 2.5,
    "GL": 2.2,
}

# Median Brutto-Haushaltseinkommen CHF/Jahr pro Kanton, Annaeherung 2024.
# Quelle: BFS HABE / Steuerstatistik.
_MEDIAN_HOUSEHOLD_INCOME_CHF: dict[str, int] = {
    "ZH": 95_000, "GE": 90_000, "ZG": 110_000, "BS": 85_000, "BL": 92_000,
    "VD": 85_000, "BE": 80_000, "LU": 82_000, "SZ": 95_000, "NW": 95_000,
    "OW": 78_000, "UR": 75_000, "GR": 78_000, "TI": 75_000, "VS": 72_000,
    "FR": 80_000, "NE": 73_000, "JU": 70_000, "SO": 80_000, "AG": 88_000,
    "SG": 80_000, "TG": 82_000, "SH": 80_000, "AR": 78_000, "AI": 75_000,
    "GL": 75_000,
}

# Schweizer Median-Haushaltseinkommen 2024 (Brutto, Annaeherung BFS HABE).
NATIONAL_MEDIAN_HOUSEHOLD_INCOME_CHF = 82_000


class CantonNotCoveredError(ValueError):
    """Kanton ist nicht in der BFS-Tabelle hinterlegt."""


class MunicipalityNotCoveredError(ValueError):
    """Gemeinde ist nicht in der Population-Tabelle hinterlegt."""


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


def get_population(municipality: str) -> int:
    """Bevoelkerungszahl fuer eine Gemeinde (Annaeherung 2024).

    Raises:
        MunicipalityNotCoveredError: wenn die Gemeinde nicht in der
            Tabelle ist (typisch wenn die ZIP-Tabelle erweitert wird,
            ohne hier nachzuziehen).
    """
    if municipality not in _POPULATION_BY_MUNICIPALITY:
        raise MunicipalityNotCoveredError(
            f"Gemeinde {municipality!r} hat keinen Population-Eintrag in der "
            f"MVP-Tabelle. Bitte _POPULATION_BY_MUNICIPALITY in bfs.py ergaenzen."
        )
    return _POPULATION_BY_MUNICIPALITY[municipality]


def get_median_rent_chf_per_m2(canton: str) -> float:
    if canton not in _MEDIAN_RENT_CHF_PER_M2:
        raise CantonNotCoveredError(
            f"Kanton {canton!r} hat keinen Median-Mietpreis-Eintrag."
        )
    return _MEDIAN_RENT_CHF_PER_M2[canton]


def get_avg_age(canton: str) -> float:
    if canton not in _AVG_AGE:
        raise CantonNotCoveredError(f"Kanton {canton!r} hat keinen avg_age-Eintrag.")
    return _AVG_AGE[canton]


def get_avg_household_size(canton: str) -> float:
    if canton not in _AVG_HOUSEHOLD_SIZE:
        raise CantonNotCoveredError(
            f"Kanton {canton!r} hat keinen avg_household_size-Eintrag."
        )
    return _AVG_HOUSEHOLD_SIZE[canton]


def get_median_household_income_chf(canton: str) -> int:
    if canton not in _MEDIAN_HOUSEHOLD_INCOME_CHF:
        raise CantonNotCoveredError(
            f"Kanton {canton!r} hat keinen Median-Einkommen-Eintrag."
        )
    return _MEDIAN_HOUSEHOLD_INCOME_CHF[canton]
