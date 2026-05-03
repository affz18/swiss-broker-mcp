"""Akquise-Strategien fuer Verkaeufer- und Kaeufer-Mails.

Internes Modul (Underscore-Prefix) - nur von src/tools/acquisition.py
genutzt. Hier liegen die strategiespezifischen Texte (Talking Points,
Personalisierungs-Hints, Subject Lines) sowie die Builder-Funktionen,
die Templates mit Marktdaten zu fertigen Strings formatieren.

Asymmetrie-Design:
- SELLER fokussiert auf yoy_change_percent (Wertsteigerung als
  Verkaufs-Trigger), Verkaeufermarkt-Narrativ, kostenlose Bewertung
  als CTA.
- BUYER fokussiert auf vacancy_rate_percent (knappes Angebot),
  Off-market-Pipeline, langfristige Pflege.

TODO (v0.3): "Hooks" (lokale Bauprojekte, Schul-Erweiterungen,
OeV-Ausbau) sind aktuell generisch ("Erwaehne lokale Entwicklung").
Spaeter: Live-Anbindung an OSM Overpass + kommunale RSS/News-Feeds,
sodass das Tool konkrete lokale Anker liefert (z.B. "Neue Sekundar-
schule Stans 2026"). Bis dahin generischer Hint, ehrlicher als
hand-kuratierte Staticdaten die schnell veralten.
"""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

TargetAudience = Literal["potential_seller", "potential_buyer"]


class StrategyContext(TypedDict):
    """Kontext fuer die Strategy-Builder (alle relevanten Marktdaten + Texte)."""

    municipality: str
    canton: str
    canton_name: str
    yoy_change_percent: float
    vacancy_rate_percent: float
    property_type_de_plural: str
    is_fallback: bool  # True wenn ZIP unbekannt, nationale Defaults verwendet


class StrategyPayload(TypedDict):
    """Output eines Strategy-Builders - wird vom Tool 1:1 in die Response gegeben."""

    market_summary: str
    talking_points: list[str]
    personalization_hints: list[str]
    suggested_subject_lines: list[str]


# --- Mapping property_type -> deutsche Pluralform ---
PROPERTY_TYPE_DE_PLURAL: dict[str, str] = {
    "apartment": "Eigentumswohnungen",
    "house": "Einfamilienhaeuser",
    "land": "Bauland-Parzellen",
}


# --- SELLER-Strategie ---

# Templates fuer Talking Points. Verfuegbare Format-Keys siehe StrategyContext.
# Zusaetzlich: {yoy_signed} ("+4.2%"), {yoy_abs} ("4.2"), {vacancy} ("0.8")
_SELLER_TALKING_POINT_TEMPLATES: list[str] = [
    "Der Markt in {municipality} ist aktuell verkaeuferfreundlich.",
    "Preise im Kanton {canton_name} {yoy_signed} in den letzten 12 Monaten "
    "(BFS Wohnimmobilienpreisindex, regional approximiert).",
    "Durchschnittliche Verkaufsdauer im Kanton {canton_name} liegt nach "
    "regionalen Marktbeobachtungen tendenziell unter 90 Tagen.",
    "Hohe Nachfrage nach {property_type_de_plural} - Inserate sind oft "
    "innerhalb weniger Wochen besichtigt.",
    "Steigende Hypothekarzinsen koennten die Marktdynamik daempfen - "
    "ein guter Verkaufszeitpunkt ist datengetrieben argumentierbar.",
    "Eine kostenlose Marktwert-Einschaetzung ist ein unverbindlicher und "
    "niederschwelliger Erstkontakt.",
]

_SELLER_PERSONALIZATION_HINTS: list[str] = [
    "Stelle Bezug zu einer aktuellen lokalen Entwicklung her "
    "(Bauprojekt, Schul-Erweiterung, OeV-Ausbau in der Gemeinde).",
    "Erwaehne die kantonale Steuerentwicklung als Zeitpunkt-Argument, "
    "wenn relevant.",
    "Verweise auf eine vergleichbare Verkaufstransaktion in der Nachbarschaft, "
    "sofern oeffentlich bekannt.",
    "Personalisiere mit Anrede + Strassennamen, falls aus oeffentlichem "
    "Grundbuch bekannt - aber kein 'Cold Stalking'.",
    "Schliesse mit einer konkreten, niederschwelligen Frage ab "
    "(Termin fuer kostenlose Bewertung).",
]

_SELLER_SUBJECT_LINE_TEMPLATES: list[str] = [
    "Ihre Immobilie in {municipality}: kostenlose Marktwert-Einschaetzung",
    "{municipality}: Verkaufspreise {yoy_signed} - was ist Ihre Liegenschaft heute wert?",
    "Kurze Frage zu Ihrer Liegenschaft in {municipality}",
]


# --- BUYER-Strategie ---

_BUYER_TALKING_POINT_TEMPLATES: list[str] = [
    "Der Wohnungsmarkt in {municipality} ist eng - eine kuratierte "
    "Begleitung erhoeht die Trefferquote spuerbar.",
    "Leerstandsquote im Kanton {canton_name}: {vacancy}% - knappes Angebot, "
    "schnelle Reaktion ist entscheidend.",
    "Off-market-Objekte machen einen erheblichen Teil des Schweizer "
    "Marktes aus - direkter Zugang ueber unser Makler-Netzwerk.",
    "Hohe Nachfrage nach {property_type_de_plural} - wer fruehzeitig "
    "Praeferenzen klaert, ist beim Match-Making vorne.",
    "Langfristige Beziehungspflege zu lokalen Eigentuemern ermoeglicht "
    "Frueherkennung neuer Inserate vor der Marktveroeffentlichung.",
    "Vergleichsregionen mit besserer Verfuegbarkeit lassen sich als "
    "Plan B vorab pruefen - kein Wunsch-Tunnel-Blick.",
]

_BUYER_PERSONALIZATION_HINTS: list[str] = [
    "Frage nach konkreten Praeferenzen (Kinderzahl, Pendlerzeit, Aussicht, "
    "Steuerfuss-Praeferenz, Mindest-/Maximalbudget).",
    "Erwaehne deine Off-market-Pipeline ohne konkrete Objekte zu nennen.",
    "Biete ein erstes unverbindliches 30-Min-Gespraech an "
    "(persoenlich oder online).",
    "Verweise auf eine Vergleichsregion mit besserer Verfuegbarkeit "
    "als Plan B (z.B. weniger zentrale Gemeinden im gleichen Kanton).",
    "Setze klare naechste Schritte: Suchprofil zusammen schaerfen vor "
    "der eigentlichen Suche.",
]

_BUYER_SUBJECT_LINE_TEMPLATES: list[str] = [
    "Suchen Sie eine Immobilie in {municipality}? Wir kennen den Markt.",
    "Off-market-Objekte in {canton_name}: lassen Sie uns sprechen",
    "Knapper Markt in {municipality} - so finden wir trotzdem Ihr Objekt",
]


def _format_template(template: str, ctx: StrategyContext, derived: dict[str, str]) -> str:
    """Format ein Template mit Context + abgeleiteten Format-Keys.

    Trennung damit Linter ueber {} Keys nicht meckert; ausserdem leichter
    testbar.
    """
    return template.format(**ctx, **derived)


def _derived_format_keys(ctx: StrategyContext) -> dict[str, str]:
    yoy = ctx["yoy_change_percent"]
    return {
        "yoy_signed": f"{yoy:+.1f}%",
        "yoy_abs": f"{abs(yoy):.1f}",
        "vacancy": f"{ctx['vacancy_rate_percent']:.1f}",
    }


def _seller_market_summary(ctx: StrategyContext) -> str:
    yoy = ctx["yoy_change_percent"]
    abs_change = abs(yoy)
    direction = "gestiegen" if yoy > 0 else "gesunken" if yoy < 0 else "stabil geblieben"
    seller_climate = (
        "Verkaeufermarkt: hohe Nachfrage, kurze Verkaufsdauer."
        if yoy > 1.0
        else "Markt ist aktuell ausgeglichen - sorgfaeltige Preisstrategie wichtig."
    )
    return (
        f"Preise im Kanton {ctx['canton_name']} sind in den letzten "
        f"12 Monaten um {abs_change:.1f}% {direction}. {seller_climate}"
    )


def _buyer_market_summary(ctx: StrategyContext) -> str:
    vacancy = ctx["vacancy_rate_percent"]
    tightness = (
        "Sehr knappes Angebot"
        if vacancy < 1.0
        else "Knappes Angebot"
        if vacancy < 1.5
        else "Moderates Angebot"
    )
    return (
        f"Im Kanton {ctx['canton_name']} liegt die Leerstandsquote bei "
        f"{vacancy:.1f}%. {tightness} - Kaeufer profitieren von professioneller "
        f"Marktkenntnis und Off-market-Zugang."
    )


def build_seller_payload(ctx: StrategyContext) -> StrategyPayload:
    derived = _derived_format_keys(ctx)
    return StrategyPayload(
        market_summary=_seller_market_summary(ctx),
        talking_points=[
            _format_template(t, ctx, derived) for t in _SELLER_TALKING_POINT_TEMPLATES
        ],
        personalization_hints=list(_SELLER_PERSONALIZATION_HINTS),
        suggested_subject_lines=[
            _format_template(t, ctx, derived) for t in _SELLER_SUBJECT_LINE_TEMPLATES
        ],
    )


def build_buyer_payload(ctx: StrategyContext) -> StrategyPayload:
    derived = _derived_format_keys(ctx)
    return StrategyPayload(
        market_summary=_buyer_market_summary(ctx),
        talking_points=[
            _format_template(t, ctx, derived) for t in _BUYER_TALKING_POINT_TEMPLATES
        ],
        personalization_hints=list(_BUYER_PERSONALIZATION_HINTS),
        suggested_subject_lines=[
            _format_template(t, ctx, derived) for t in _BUYER_SUBJECT_LINE_TEMPLATES
        ],
    )


def build_payload(audience: TargetAudience, ctx: StrategyContext) -> StrategyPayload:
    """Dispatch SELLER/BUYER -> Payload."""
    if audience == "potential_seller":
        return build_seller_payload(ctx)
    return build_buyer_payload(ctx)
