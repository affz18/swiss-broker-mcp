"""Tool: compare_locations - vergleicht 2-5 Schweizer Gemeinden.

Geeignet fuer das klassische Beratungsgespraech: ein Kunde steht
zwischen mehreren Gemeinden ("Soll ich nach Zug oder Luzern ziehen?"
oder "Cham, Zug oder Baar - wo lohnt sich der Hauskauf am meisten?").

Strategischer Mehrwert vs. Standard-LLM+WebSearch:
- Quantifizierte Deltas ("Zug ist 67% steueroptimaler") statt vager
  Aussagen ("Zug hat tiefere Steuern").
- Per-Dimension-Sieger sofort sichtbar (tax_winner, rent_winner, ...).
- Broker-Narrative: 1-3 Saetze die der Makler woertlich beim Kunden
  vortragen kann.
- Trust: alle Zahlen mit Stichdatum + Quellenangabe, keine
  Halluzinationen.

Eingabe: 2-5 PLZ. Ausgabe: strukturierter Vergleich mit Sieger-
Mapping, Deltas-Liste und Narrative-Summary in Maklersprache.

Bei mindestens einer unbekannten PLZ: UnknownZipError (kein partial
fallback - ein Vergleich mit halb-erfundenen Daten waere irrefuehrend).
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import TypeAdapter
from typing_extensions import TypedDict

from src.tools.neighborhood import NeighborhoodProfile, get_neighborhood_profile
from src.utils.disclaimers import COMPARISON_DISCLAIMER

# Pydantic-Validation: zwingt 2-5 Eintraege ueber TypeAdapter mit Schema.
_LOCATIONS_VALIDATOR: TypeAdapter[list[str]] = TypeAdapter(list[str])

# Delta-Magnitude-Schwellen (% Differenz vom kleineren Wert).
DeltaMagnitude = Literal["vergleichbar", "leicht", "deutlich", "stark"]


def _classify_magnitude(pct_diff: float) -> DeltaMagnitude:
    """Prozentuale Differenz -> Sprach-Label."""
    abs_pct = abs(pct_diff)
    if abs_pct < 5.0:
        return "vergleichbar"
    if abs_pct < 15.0:
        return "leicht"
    if abs_pct < 30.0:
        return "deutlich"
    return "stark"


class LocationSummary(TypedDict):
    """Slim-Profil eines einzelnen Standortes (subset des
    NeighborhoodProfile fuer den Vergleich)."""

    zip_code: str
    municipality: str
    canton: str
    canton_code: str
    population: int | None
    tax_multiplier: float
    tax_rank_canton: str
    vacancy_rate_percent: float
    median_rent_chf_per_m2: float
    median_household_income_chf: int
    data_quality: str


class Delta(TypedDict):
    dimension: str  # z.B. "tax_multiplier"
    label: str  # menschenlesbar, z.B. "Steuerfuss-Multiplier"
    higher_zip: str
    lower_zip: str
    higher_value: float
    lower_value: float
    pct_diff: float  # immer >= 0
    magnitude: DeltaMagnitude
    delta_text: str  # ready-to-quote, z.B. "Zug ist 67% guenstiger ..."


class Winners(TypedDict):
    """Sieger pro Dimension (PLZ-Code). None wenn alle Locations
    gleichauf sind (oder alle Werte unbekannt)."""

    lowest_tax_multiplier: str | None
    lowest_rent: str | None
    highest_income: str | None
    lowest_vacancy: str | None  # niedrige Quote = enger Markt
    largest_population: str | None


class LocationComparison(TypedDict):
    locations: list[LocationSummary]
    winners: Winners
    deltas: list[Delta]
    narrative_summary: str
    data_sources: list[str]
    disclaimer: str


def _profile_to_summary(p: NeighborhoodProfile) -> LocationSummary:
    return LocationSummary(
        zip_code=p["zip_code"],
        municipality=p["municipality"],
        canton=p["canton"],
        canton_code=p["canton_code"],
        population=p["population"],
        tax_multiplier=p["tax_multiplier"],
        tax_rank_canton=p["tax_rank_canton"],
        vacancy_rate_percent=p["vacancy_rate_percent"],
        median_rent_chf_per_m2=p["median_rent_chf_per_m2"],
        median_household_income_chf=p["demographics"]["median_household_income_chf"],
        data_quality=p["data_quality"],
    )


def _value_for(summary: LocationSummary, dim: str) -> float | None:
    """Holt einen numerischen Wert anhand des Dimension-Schluessels.

    TypedDict erlaubt nur Literal-String-Indices. Da wir hier ueber
    Dimensionen iterieren, ueber `cast` zu einem dict[str, object]
    auspacken und Typ-Check machen.
    """
    raw = cast(dict[str, object], summary).get(dim)
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _format_value(dim: str, val: float) -> str:
    """Werte-spezifische Formatierung fuer das delta_text."""
    if dim == "tax_multiplier":
        return f"{val:.2f}"
    if dim == "median_rent_chf_per_m2":
        return f"{val:.2f} CHF/m2"
    if dim == "median_household_income_chf":
        return f"{int(val):,} CHF".replace(",", "'")
    if dim == "vacancy_rate_percent":
        return f"{val:.1f}%"
    return f"{val}"


# Pro Dimension: formatter der ein delta_text fuer (winner_municipality,
# loser_municipality, winner_val, loser_val, savings_pct, magnitude) baut.
# `savings_pct` ist konsistent (higher - lower) / higher * 100 fuer
# "lower is better"-Dimensionen, sodass "X% guenstiger" linguistisch
# stimmt (max 100%, nie negativ).
def _format_tax_delta(
    win_mun: str, lose_mun: str, win_val: float, lose_val: float,
    savings_pct: float, magnitude: DeltaMagnitude,
) -> str:
    # Caveat dass Multiplier kantonsweit nicht direkt vergleichbar ist:
    # tax_rank_canton ist im LocationSummary fuer den querkantonalen
    # Vergleich, der LLM kann das bei Bedarf erwaehnen.
    return (
        f"{win_mun} ist {magnitude} steueroptimaler als {lose_mun} "
        f"({savings_pct:.0f}% guenstiger, Multiplier {win_val:.2f} "
        f"vs {lose_val:.2f})."
    )


def _format_rent_delta(
    win_mun: str, lose_mun: str, win_val: float, lose_val: float,
    savings_pct: float, magnitude: DeltaMagnitude,
) -> str:
    return (
        f"{win_mun} ist {magnitude} guenstiger bei der Miete als "
        f"{lose_mun} ({savings_pct:.0f}% tiefer, "
        f"{win_val:.2f} CHF/m2 vs {lose_val:.2f} CHF/m2)."
    )


def _format_income_delta(
    win_mun: str, lose_mun: str, win_val: float, lose_val: float,
    gain_pct: float, magnitude: DeltaMagnitude,
) -> str:
    # Schweizer Tausendertrennzeichen nur auf den Zahlen, nicht im
    # restlichen Text (sonst werden auch Format-Kommas ersetzt).
    win_str = f"{int(win_val):,}".replace(",", "'")
    lose_str = f"{int(lose_val):,}".replace(",", "'")
    return (
        f"{win_mun} liegt {magnitude} hoeher beim Median-Haushaltseinkommen "
        f"als {lose_mun} (+{gain_pct:.0f}%, {win_str} CHF vs {lose_str} CHF)."
    )


def _format_vacancy_delta(
    tighter_mun: str, looser_mun: str, tighter_val: float, looser_val: float,
    spread_pct: float, magnitude: DeltaMagnitude,
) -> str:
    # Niedrige Vacancy = enger Markt - sprachlich neutral, NICHT
    # "guenstiger" (das waere fuer den Kaeufer kein Vorteil).
    return (
        f"{tighter_mun} hat einen {magnitude} engeren Wohnungsmarkt als "
        f"{looser_mun} (Leerstand {tighter_val:.1f}% vs {looser_val:.1f}%). "
        f"Enger Markt = weniger Angebot, schnelleres Handeln noetig."
    )


# (dim_key, label, direction, formatter)
# direction: "lower_better" | "higher_better" | "neutral"
_NUMERIC_DIMENSIONS: list[tuple[str, str, str]] = [
    ("tax_multiplier", "Steuerfuss-Multiplier", "lower_better"),
    ("median_rent_chf_per_m2", "Median-Miete CHF/m2", "lower_better"),
    ("median_household_income_chf", "Median-Haushaltseinkommen", "higher_better"),
    ("vacancy_rate_percent", "Leerstandsquote %", "neutral"),
]


def _build_delta(
    dim: str,
    label: str,
    direction: str,
    summaries: list[LocationSummary],
) -> Delta | None:
    """Erzeugt einen Delta-Eintrag fuer eine Dimension. Returns None
    wenn weniger als 2 Werte verfuegbar oder alle Werte gleich.
    """
    values: list[tuple[str, str, float]] = []
    for s in summaries:
        v = _value_for(s, dim)
        if v is not None:
            values.append((s["zip_code"], s["municipality"], v))

    if len(values) < 2:
        return None

    high = max(values, key=lambda x: x[2])
    low = min(values, key=lambda x: x[2])
    if high[2] == low[2]:
        return None

    if direction == "lower_better":
        # "X% guenstiger" - savings vom hoeheren Wert.
        pct = (high[2] - low[2]) / high[2] * 100 if high[2] != 0 else 0.0
        magnitude = _classify_magnitude(pct)
        if dim == "tax_multiplier":
            delta_text = _format_tax_delta(
                low[1], high[1], low[2], high[2], pct, magnitude
            )
        else:  # rent
            delta_text = _format_rent_delta(
                low[1], high[1], low[2], high[2], pct, magnitude
            )
    elif direction == "higher_better":
        # "X% hoeher" - gain ueber den niedrigeren Wert.
        pct = (high[2] - low[2]) / low[2] * 100 if low[2] != 0 else 0.0
        magnitude = _classify_magnitude(pct)
        delta_text = _format_income_delta(
            high[1], low[1], high[2], low[2], pct, magnitude
        )
    else:  # neutral - vacancy
        # Spread auf den hoeheren Wert (wie viel Prozent enger).
        pct = (high[2] - low[2]) / high[2] * 100 if high[2] != 0 else 0.0
        magnitude = _classify_magnitude(pct)
        delta_text = _format_vacancy_delta(
            low[1], high[1], low[2], high[2], pct, magnitude
        )

    return Delta(
        dimension=dim,
        label=label,
        higher_zip=high[0],
        lower_zip=low[0],
        higher_value=high[2],
        lower_value=low[2],
        pct_diff=round(pct, 1),
        magnitude=magnitude,
        delta_text=delta_text,
    )


def _compute_winners(summaries: list[LocationSummary]) -> Winners:
    def _argmin_zip(dim: str) -> str | None:
        candidates = [
            (s["zip_code"], _value_for(s, dim))
            for s in summaries
            if _value_for(s, dim) is not None
        ]
        if len(candidates) < 1:
            return None
        return min(candidates, key=lambda x: x[1] or 0.0)[0]

    def _argmax_zip(dim: str) -> str | None:
        candidates = [
            (s["zip_code"], _value_for(s, dim))
            for s in summaries
            if _value_for(s, dim) is not None
        ]
        if len(candidates) < 1:
            return None
        return max(candidates, key=lambda x: x[1] or 0.0)[0]

    population_candidates = [
        (s["zip_code"], s["population"])
        for s in summaries
        if s["population"] is not None
    ]
    largest_pop = (
        max(population_candidates, key=lambda x: x[1] or 0)[0]
        if population_candidates
        else None
    )

    return Winners(
        lowest_tax_multiplier=_argmin_zip("tax_multiplier"),
        lowest_rent=_argmin_zip("median_rent_chf_per_m2"),
        highest_income=_argmax_zip("median_household_income_chf"),
        lowest_vacancy=_argmin_zip("vacancy_rate_percent"),
        largest_population=largest_pop,
    )


def _build_narrative(deltas: list[Delta], summaries: list[LocationSummary]) -> str:
    """1-3 Saetze in Maklersprache, fokussiert auf die staerksten Deltas.

    Strategie: nimm die Top-2 staerksten Deltas (nach magnitude +
    pct_diff) und formuliere ein zusammenfassendes Statement.
    """
    if not deltas:
        names = " / ".join(s["municipality"] for s in summaries)
        return (
            f"Die Standorte ({names}) sind ueber alle verglichenen "
            f"Dimensionen hinweg vergleichbar - kein klarer Sieger."
        )

    magnitude_rank = {"stark": 4, "deutlich": 3, "leicht": 2, "vergleichbar": 1}
    sorted_deltas = sorted(
        deltas,
        key=lambda d: (magnitude_rank[d["magnitude"]], d["pct_diff"]),
        reverse=True,
    )
    top = sorted_deltas[:2]
    sentences = [d["delta_text"] for d in top]

    # Optional: kurzer "Recommendation"-Satz wenn klare Sieger-Muster.
    municipalities = sorted({s["municipality"] for s in summaries})
    if len(top) >= 2:
        sentences.append(
            f"Fazit fuer das Beratungsgespraech: Trade-off zwischen "
            f"{top[0]['label']} und {top[1]['label']} - die Wahl haengt "
            f"davon ab, welche Dimension dem Kunden wichtiger ist "
            f"({' vs. '.join(municipalities)})."
        )

    return " ".join(sentences)


async def compare_locations(zip_codes: list[str]) -> LocationComparison:
    """Vergleicht 2-5 Schweizer Gemeinden anhand quantifizierbarer
    Markt- und Steuer-Dimensionen.

    Args:
        zip_codes: Liste von 2-5 vier-stelligen Schweizer PLZ
            (z.B. ``["6300", "6003"]`` fuer Zug vs Luzern).

    Returns:
        LocationComparison mit:
        - locations: slim Summary pro Standort
        - winners: Sieger pro Dimension (lowest_tax / lowest_rent / ...)
        - deltas: pro Dimension ein quantifiziertes Delta inkl.
          ready-to-quote ``delta_text``
        - narrative_summary: 1-3 Saetze in Maklersprache fuer das
          Beratungsgespraech, fokussiert auf die staerksten Trade-offs
        - data_sources, disclaimer

    Raises:
        ValueError: weniger als 2 oder mehr als 5 PLZ uebergeben.
        UnknownZipError: mindestens eine PLZ ist nicht im Schweizer
            PLZ-Register.
    """
    _LOCATIONS_VALIDATOR.validate_python(zip_codes)
    if not 2 <= len(zip_codes) <= 5:
        raise ValueError(
            f"compare_locations erwartet 2-5 PLZ, bekam {len(zip_codes)}. "
            f"Fuer Einzel-Profil get_neighborhood_profile nutzen, fuer "
            f"groessere Vergleiche bitte einzeln zerlegen."
        )

    # Profile parallel laden (alle Tools sind embedded -> trivial fast,
    # aber asyncio.gather macht das Code-strukturell sauber fuer den
    # Tag an dem live HTTP-Calls reinkommen).
    import asyncio

    profiles = await asyncio.gather(
        *(get_neighborhood_profile(z) for z in zip_codes)
    )

    summaries = [_profile_to_summary(p) for p in profiles]

    deltas: list[Delta] = []
    for dim, label, direction in _NUMERIC_DIMENSIONS:
        d = _build_delta(dim, label, direction, summaries)
        if d is not None:
            deltas.append(d)

    winners = _compute_winners(summaries)
    narrative = _build_narrative(deltas, summaries)

    # Quellen aus dem ersten Profil uebernehmen (alle nutzen gleiche).
    data_sources = list(profiles[0]["data_sources"])

    return LocationComparison(
        locations=summaries,
        winners=winners,
        deltas=deltas,
        narrative_summary=narrative,
        data_sources=data_sources,
        disclaimer=COMPARISON_DISCLAIMER,
    )


__all__ = [
    "Delta",
    "DeltaMagnitude",
    "LocationComparison",
    "LocationSummary",
    "Winners",
    "compare_locations",
]
