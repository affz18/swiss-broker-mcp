"""Tool: valuate_property - Immobilienbewertung auf Basis oeffentlicher Daten.

Nutzt BFS-basierte regionale Quadratmeterpreise und kantonale
Year-over-Year-Trends, um eine grobe Schaetzung fuer eine Schweizer
Immobilie zu liefern.

KEIN Ersatz fuer eine professionelle Schaetzung. Der Disclaimer ist
deshalb fester Bestandteil des Outputs - das LLM soll ihn dem User
zeigen.

Berechnungsmodell (transparent gehalten):

  base = BASE_PRICE_PER_M2[canton][property_type]
  multiplier = condition_factor * year_built_factor
  price_per_m2 = round(base * multiplier)
  estimated_value = price_per_m2 * size_m2
  range = +/- 12% (Schwankung typischer Schweizer Marktangebote)

Modifikatoren:
  - condition: renovated +10%, good +/- 0%, needs_work -15%
  - year_built: <=1980 -10%, 1980-2010 +/- 0%, >=2010 +5% (nur wenn
    nicht ohnehin als "renovated" markiert, sonst wuerde der Bonus
    doppelt zaehlen).
"""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

from src.data_sources.bfs import (
    DATA_SOURCE_LABEL,
    PropertyType,
    get_base_price_per_m2,
    get_yoy_change_percent,
)
from src.utils.disclaimers import VALUATION_BROKER_NOTES, VALUATION_DISCLAIMER
from src.utils.swiss_zip import UnknownZipError, lookup_zip

Condition = Literal["renovated", "good", "needs_work"]
ConfidenceLevel = Literal["high", "medium", "low"]


class PriceRange(TypedDict):
    min: int
    max: int


class ValuationResult(TypedDict):
    estimated_value_chf: int
    price_range_chf: PriceRange
    price_per_m2: int
    comparable_region: str
    data_sources: list[str]
    confidence: ConfidenceLevel
    market_context: str
    broker_notes: str
    disclaimer: str


# Range +/- in Prozent (typische Schwankung in der Schweiz).
_RANGE_SPREAD_PCT = 0.12


def _condition_multiplier(condition: Condition) -> float:
    return {
        "renovated": 1.10,
        "good": 1.00,
        "needs_work": 0.85,
    }[condition]


def _year_built_multiplier(year_built: int | None, condition: Condition) -> float:
    """Alters-Faktor. Nur fuer non-renovated Objekte; renovierte Objekte
    bekommen den Bonus schon ueber den condition-Multiplier.
    """
    if year_built is None or condition == "renovated":
        return 1.0
    if year_built <= 1980:
        return 0.90
    if year_built >= 2010:
        return 1.05
    return 1.0


def _confidence(
    canton: str,
    property_type: PropertyType,
    rooms: float,
    size_m2: int,
) -> ConfidenceLevel:
    """Heuristische Confidence-Einstufung.

    - low:     extreme Werte (Mini- oder Riesen-Wohnung), implausible
               Zimmer/m2-Ratio.
    - medium:  Standardfall - regional aggregierte Daten, keine
               Besichtigung.
    - high:    aktuell nicht erreichbar (Vorbehalt fuer spaetere
               Versionen mit Live-Daten + lokalem Mikrolage-Faktor).
    """
    # Heuristik: typisch sind 20-35m2 pro Zimmer
    m2_per_room = size_m2 / rooms if rooms > 0 else 0
    if size_m2 < 25 or size_m2 > 600:
        return "low"
    if m2_per_room < 12 or m2_per_room > 60:
        return "low"
    if property_type == "land" and rooms > 0:
        # Bauland hat keine Zimmer - inkonsistente Eingabe
        return "low"
    _ = canton  # Reserviert fuer kuenftige kanton-spezifische Heuristiken.
    return "medium"


def _format_market_context(canton_name: str, yoy_change: float) -> str:
    if yoy_change > 0:
        direction = "gestiegen"
    elif yoy_change < 0:
        direction = "gesunken"
    else:
        direction = "stabil geblieben"
    abs_change = abs(yoy_change)
    return (
        f"Preise im Kanton {canton_name} sind in den letzten 12 Monaten "
        f"um {abs_change:.1f}% {direction}."
    )


def _validate_inputs(
    property_type: str,
    size_m2: int,
    rooms: float,
    condition: str,
    year_built: int | None,
) -> None:
    if property_type not in ("apartment", "house", "land"):
        raise ValueError(
            f"property_type {property_type!r} ungueltig. "
            f"Erlaubt: 'apartment', 'house', 'land'."
        )
    if condition not in ("renovated", "good", "needs_work"):
        raise ValueError(
            f"condition {condition!r} ungueltig. "
            f"Erlaubt: 'renovated', 'good', 'needs_work'."
        )
    if size_m2 <= 0:
        raise ValueError(f"size_m2 muss > 0 sein, ist {size_m2}.")
    if rooms < 0:
        raise ValueError(f"rooms darf nicht negativ sein, ist {rooms}.")
    if year_built is not None and (year_built < 1800 or year_built > 2100):
        raise ValueError(
            f"year_built {year_built} unplausibel (erlaubt: 1800-2100)."
        )


async def valuate_property(
    zip_code: str,
    property_type: PropertyType,
    size_m2: int,
    rooms: float,
    condition: Condition,
    year_built: int | None = None,
) -> ValuationResult:
    """Schaetzt den Marktwert einer Schweizer Immobilie.

    Liefert eine grobe Bewertung anhand kantonaler Mittelwerte (BFS
    Wohnimmobilienpreisindex) plus Modifikatoren fuer Zustand und
    Baujahr. Geeignet fuer eine erste Einschaetzung im
    Maklergespraech - NICHT als rechtsverbindliche Bewertung.

    Args:
        zip_code: 4-stellige Schweizer Postleitzahl (z.B. "6060" fuer Sarnen).
        property_type: Art der Immobilie - "apartment" (Wohnung),
            "house" (Einfamilienhaus) oder "land" (Bauland).
        size_m2: Wohnflaeche in Quadratmetern (bei Bauland: Grundstueck).
        rooms: Zimmerzahl (Schweizer Konvention: 3.5, 4, 4.5 ...).
            Bei Bauland kann 0 angegeben werden.
        condition: Zustand - "renovated" (kuerzlich saniert), "good"
            (gepflegt, normaler Zustand) oder "needs_work" (sanierungs-
            beduerftig).
        year_built: Baujahr (optional). Wird mit condition kombiniert,
            um den Alters-Abschlag zu berechnen.

    Returns:
        ValuationResult mit:
        - estimated_value_chf: Geschaetzter Gesamtwert in CHF
        - price_range_chf: Min/Max Spanne (+/- 12%)
        - price_per_m2: Preis pro m2 nach Modifikatoren
        - comparable_region: Textuelle Beschreibung der Vergleichsregion
        - data_sources: Liste der genutzten Datenquellen (Quellenangabe!)
        - confidence: "high" | "medium" | "low"
        - market_context: Kurzer Satz zur Marktentwicklung
        - broker_notes: Hinweise fuer den Makler (Vor-Ort-Termin etc.)
        - disclaimer: Verbindlicher Disclaimer

    Raises:
        UnknownZipError: PLZ ist nicht in der Tabelle hinterlegt.
        ValueError: Eingabe-Validierung fehlgeschlagen (z.B. negativer
            size_m2, ungueltiger property_type).
    """
    _validate_inputs(property_type, size_m2, rooms, condition, year_built)

    location = lookup_zip(zip_code)  # raises UnknownZipError
    canton = location["canton"]
    canton_name = location["canton_name"]
    municipality = location["municipality"]

    base = get_base_price_per_m2(canton, property_type)
    multiplier = _condition_multiplier(condition) * _year_built_multiplier(
        year_built, condition
    )
    price_per_m2 = round(base * multiplier)
    estimated_value = price_per_m2 * size_m2

    spread = int(estimated_value * _RANGE_SPREAD_PCT)
    price_range: PriceRange = {
        "min": estimated_value - spread,
        "max": estimated_value + spread,
    }

    yoy_change = get_yoy_change_percent(canton)

    return ValuationResult(
        estimated_value_chf=estimated_value,
        price_range_chf=price_range,
        price_per_m2=price_per_m2,
        comparable_region=f"{municipality} + Umgebung Kanton {canton_name}",
        data_sources=[DATA_SOURCE_LABEL],
        confidence=_confidence(canton, property_type, rooms, size_m2),
        market_context=_format_market_context(canton_name, yoy_change),
        broker_notes=VALUATION_BROKER_NOTES,
        disclaimer=VALUATION_DISCLAIMER,
    )


# Re-export fuer einfacheren Import von aussen.
__all__ = [
    "Condition",
    "ConfidenceLevel",
    "PriceRange",
    "PropertyType",
    "UnknownZipError",
    "ValuationResult",
    "valuate_property",
]
