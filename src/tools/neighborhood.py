"""Tool: get_neighborhood_profile - Profil einer Schweizer Gemeinde / PLZ.

Aggregiert die fuer ein Maklergespraech wichtigsten Datenpunkte einer
Gemeinde in EINEM strukturierten Output:

- Population (BFS STATPOP, gemeindespezifisch wo verfuegbar)
- Steuerfuss + querkantonaler Steuer-Rang (ESTV)
- Leerstandsquote + Median-Miete (BFS, kantonal)
- Demografie: Durchschnittsalter, Haushaltsgroesse, Median-Einkommen
  inkl. faktischer Vergleich zum CH-Median
- Infrastruktur: Schulen + OeV (regelbasiert anhand Gemeinde-Groesse)

Bei unbekannter PLZ: harte UnknownZipError (ein Profil mit nationalen
Mittelwerten waere irrefuehrend).

Bei bekannter PLZ aber fehlender Gemeinde-Population (kein Eintrag in
der kuratierten ~40-Gemeinden-Tabelle): graceful fallback - das Tool
liefert ein vollstaendiges kantonales Profil und signalisiert die
Einschraenkung via `data_quality: "partial"`. Die Schul-/OeV-
Heuristik wird in dem Fall durch generischere Strings ersetzt.

TODO (v0.2): Population-Tabelle auf alle ~2147 Schweizer Gemeinden
ausweiten (BFS STATPOP CSV). Bis dahin: data_quality="partial" fuer
Gemeinden ausserhalb der MVP-Liste.

TODO (v0.3): Live-Anbindung an OSM Overpass fuer:
- highway_access_km (echte Distanz zur naechsten Autobahn-Auffahrt)
- nahe Schulen / OeV-Stops (statt Pauschal-Beschreibung)
"""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

from src.data_sources.bfs import (
    DEMOGRAPHICS_SOURCE_LABEL,
    NATIONAL_MEDIAN_HOUSEHOLD_INCOME_CHF,
    get_avg_age,
    get_avg_household_size,
    get_median_household_income_chf,
    get_median_rent_chf_per_m2,
    get_population,
    get_vacancy_rate_percent,
)
from src.data_sources.tax_data import TAX_DATA_SOURCE_LABEL, TaxRank, get_tax_info
from src.utils.disclaimers import NEIGHBORHOOD_DISCLAIMER
from src.utils.swiss_zip import UnknownZipError, lookup_zip

DataQuality = Literal["full", "partial"]


class InfrastructureInfo(TypedDict):
    schools: list[str]
    public_transport: str
    highway_access_km: float | None  # None wenn fuer MVP nicht verfuegbar


class DemographicsInfo(TypedDict):
    avg_age: float
    avg_household_size: float
    median_household_income_chf: int
    income_context: str  # faktischer Vergleich zum CH-Median


class NeighborhoodProfile(TypedDict):
    zip_code: str
    municipality: str
    canton: str  # vollstaendiger Name (z.B. "Obwalden")
    canton_code: str  # 2-Buchstaben (z.B. "OW")
    population: int | None  # None bei data_quality="partial"
    tax_multiplier: float
    tax_rank_canton: TaxRank
    tax_multiplier_note: str
    vacancy_rate_percent: float
    median_rent_chf_per_m2: float
    infrastructure: InfrastructureInfo
    demographics: DemographicsInfo
    data_quality: DataQuality
    data_sources: list[str]
    disclaimer: str


def _format_chf(amount: int) -> str:
    """Schweizer Tausendertrennzeichen: 82'000."""
    return f"{amount:,}".replace(",", "'")


def _build_income_context(canton_median: int, national_median: int) -> str:
    """Faktischer Vergleichstext zum Schweizer Median (kein 'low/high')."""
    diff = canton_median - national_median
    if national_median == 0:
        return f"Schweizer Median: {_format_chf(national_median)} CHF."
    pct = abs(diff) / national_median * 100
    national_str = _format_chf(national_median)
    if pct < 1.0:
        return f"Liegt im Bereich des Schweizer Medians ({national_str} CHF)."
    direction = "ueber" if diff > 0 else "unter"
    return (
        f"Liegt {pct:.0f}% {direction} dem Schweizer Median ({national_str} CHF)."
    )


def _schools_descriptor(population: int | None) -> list[str]:
    """Regelbasierte Schul-Liste anhand Gemeinde-Groesse.

    Bei unbekannter Gemeinde-Groesse: ehrlicher Minimal-Default
    (jede Schweizer Gemeinde hat eine Primarschule oder einen
    Schulverbund mit Nachbargemeinden).
    """
    if population is None:
        return ["Primarschule (oder Schulverbund mit Nachbargemeinden)"]
    schools = ["Primarschule"]
    if population >= 5_000:
        schools.append("Sekundarschule")
    if population >= 30_000:
        schools.append("Gymnasium / Mittelschule")
    return schools


def _public_transport_descriptor(population: int | None) -> str:
    """Regelbasierter OeV-Descriptor anhand Gemeinde-Groesse."""
    if population is None:
        return (
            "OeV-Anbindung variiert je nach Gemeinde - typischerweise Postauto "
            "und/oder regionale Bus-/Bahnlinien. Fuer konkrete Fahrplaene "
            "fahrplan.sbb.ch konsultieren."
        )
    if population >= 100_000:
        return "Sehr gute OeV-Anbindung (Hauptbahnhof, Tram-/Bus-Netz, S-Bahn)."
    if population >= 30_000:
        return "Gute OeV-Anbindung (Bahnhof, regionale S-Bahn, lokale Buslinien)."
    if population >= 10_000:
        return (
            "Gute OeV-Anbindung (Bahn-/S-Bahn-Halt im Ort, lokale Buslinien)."
        )
    if population >= 3_000:
        return (
            "Solide OeV-Anbindung (regionale Bahn- oder Buslinien, "
            "Halt im Dorfkern)."
        )
    return "Lokale OeV-Anbindung ueber Postauto / regionale Buslinien."


async def get_neighborhood_profile(zip_code: str) -> NeighborhoodProfile:
    """Liefert ein vollstaendiges Profil einer Schweizer Gemeinde / PLZ.

    Geeignet fuer Makler-Beratung, Akquise-Vorbereitung und Expose-
    Daten. Aggregiert oeffentliche Daten (BFS, ESTV) und
    Infrastruktur-Heuristik in einem strukturierten Output.

    Args:
        zip_code: 4-stellige Schweizer PLZ (z.B. "6060" fuer Sarnen).

    Returns:
        NeighborhoodProfile. Wenn `data_quality == "full"`: Population
        + voll-aufgeloeste Schul-/OeV-Heuristik. Wenn
        `data_quality == "partial"`: Population ist None, Schul- und
        OeV-Beschreibungen sind generisch. In beiden Faellen sind
        kantonale Daten (Steuern, Mieten, Demografie) vollstaendig.

    Raises:
        UnknownZipError: PLZ existiert nicht im Schweizer PLZ-Register.
        TaxDataNotCoveredError: Kanton hat keinen Steuer-Eintrag (sollte
            nicht auftreten - alle 26 Kantone sind abgedeckt).
    """
    location = lookup_zip(zip_code)  # raises UnknownZipError
    municipality = location["municipality"]
    canton_code = location["canton"]
    canton_name = location["canton_name"]

    population = get_population(municipality)
    data_quality: DataQuality = "full" if population is not None else "partial"

    vacancy = get_vacancy_rate_percent(canton_code)
    median_rent = get_median_rent_chf_per_m2(canton_code)
    avg_age = get_avg_age(canton_code)
    avg_household = get_avg_household_size(canton_code)
    median_income = get_median_household_income_chf(canton_code)
    tax_info = get_tax_info(zip_code, canton_code)

    return NeighborhoodProfile(
        zip_code=zip_code,
        municipality=municipality,
        canton=canton_name,
        canton_code=canton_code,
        population=population,
        tax_multiplier=tax_info["multiplier"],
        tax_rank_canton=tax_info["rank_canton"],
        tax_multiplier_note=tax_info["multiplier_note"],
        vacancy_rate_percent=vacancy,
        median_rent_chf_per_m2=median_rent,
        infrastructure=InfrastructureInfo(
            schools=_schools_descriptor(population),
            public_transport=_public_transport_descriptor(population),
            highway_access_km=None,
        ),
        demographics=DemographicsInfo(
            avg_age=avg_age,
            avg_household_size=avg_household,
            median_household_income_chf=median_income,
            income_context=_build_income_context(
                median_income, NATIONAL_MEDIAN_HOUSEHOLD_INCOME_CHF
            ),
        ),
        data_quality=data_quality,
        data_sources=[
            DEMOGRAPHICS_SOURCE_LABEL,
            TAX_DATA_SOURCE_LABEL,
        ],
        disclaimer=NEIGHBORHOOD_DISCLAIMER,
    )


__all__ = [
    "DataQuality",
    "DemographicsInfo",
    "InfrastructureInfo",
    "NeighborhoodProfile",
    "UnknownZipError",
    "get_neighborhood_profile",
]
