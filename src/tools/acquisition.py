"""Tool: get_acquisition_email_context - Daten fuer Akquise-Mails.

Liefert dem LLM regionale Markt-Insights, Talking Points, Personali-
sierungs-Hints und Subject-Line-Vorschlaege, damit der Makler in seinem
Chat-Client (Claude Desktop o.ae.) eine personalisierte Akquise-Mail
generieren kann.

Wichtig: Dieses Tool generiert KEINE Mail. Es liefert strukturierten
Kontext. Den eigentlichen Text schreibt der LLM beim Nutzer (Stil,
Anrede, Signatur).

Asymmetrie:
- target_audience="potential_seller": Tone "jetzt verkaufen", focus
  YoY-Wachstum, Verkaeufermarkt, niedrige Verkaufsdauer, CTA =
  kostenlose Bewertung.
- target_audience="potential_buyer": Tone "wir helfen im engen Markt",
  focus Leerstandsquote, Off-market-Zugang, Vergleichsregionen,
  langfristige Pflege.

Bei unbekannter PLZ: graceful fallback auf nationale Mittelwerte mit
transparentem Hinweis in data_sources.
"""

from __future__ import annotations

from typing import Literal

from pydantic import TypeAdapter
from typing_extensions import TypedDict

from src.data_sources.bfs import (
    DATA_SOURCE_LABEL,
    NATIONAL_VACANCY_RATE_PERCENT,
    NATIONAL_YOY_CHANGE_PERCENT,
    PropertyType,
    get_vacancy_rate_percent,
    get_yoy_change_percent,
)
from src.tools._acquisition_strategies import (
    PROPERTY_TYPE_DE_PLURAL,
    StrategyContext,
    TargetAudience,
    build_payload,
)
from src.utils.disclaimers import ACQUISITION_DISCLAIMER
from src.utils.swiss_zip import UnknownZipError, lookup_zip

TrendDirection = Literal["rising", "falling", "stable"]

# Pydantic TypeAdapter, damit ungueltige target_audience / property_type
# zu pydantic.ValidationError fuehren (anstatt manuellem ValueError).
# Sorgt fuer einheitliches Verhalten zwischen direktem Aufruf und
# FastMCP-Aufruf vom MCP-Client.
_TARGET_AUDIENCE_VALIDATOR: TypeAdapter[TargetAudience] = TypeAdapter(TargetAudience)
_PROPERTY_TYPE_VALIDATOR: TypeAdapter[PropertyType] = TypeAdapter(PropertyType)


class TrendData(TypedDict):
    yoy_change_percent: float
    trend_direction: TrendDirection
    data_period: str


class AcquisitionEmailContext(TypedDict):
    region_name: str
    canton: str  # 2-Buchstaben Code, "CH" bei Fallback
    target_audience: TargetAudience
    market_summary: str
    trend_data: TrendData
    talking_points: list[str]
    personalization_hints: list[str]
    suggested_subject_lines: list[str]
    data_sources: list[str]
    disclaimer: str


_DATA_PERIOD = "12-Monats-Trend (Annaeherung BFS Wohnimmobilienpreisindex 2024)"


def _trend_direction(yoy: float) -> TrendDirection:
    if yoy > 0.5:
        return "rising"
    if yoy < -0.5:
        return "falling"
    return "stable"


def _resolve_context(
    zip_code: str,
    property_type: PropertyType,
) -> tuple[StrategyContext, list[str]]:
    """Loest PLZ -> Marktdaten auf. Bei unbekannter PLZ: nationale Defaults.

    Returns:
        (context, data_sources_list). data_sources_list enthaelt das
        Standard-BFS-Label und ggf. einen Fallback-Hinweis.
    """
    try:
        location = lookup_zip(zip_code)
        municipality = location["municipality"]
        canton = location["canton"]
        canton_name = location["canton_name"]
        yoy = get_yoy_change_percent(canton)
        vacancy = get_vacancy_rate_percent(canton)
        is_fallback = False
        data_sources = [DATA_SOURCE_LABEL]
    except UnknownZipError:
        municipality = "der Schweiz"
        canton = "CH"
        canton_name = "Schweiz"
        yoy = NATIONAL_YOY_CHANGE_PERCENT
        vacancy = NATIONAL_VACANCY_RATE_PERCENT
        is_fallback = True
        data_sources = [
            DATA_SOURCE_LABEL,
            (
                f"Hinweis: PLZ {zip_code!r} nicht in der Lookup-Tabelle - "
                f"nationale Schweizer Mittelwerte verwendet. Fuer praezisere "
                f"Daten bitte mit einer abgedeckten PLZ aus der gleichen "
                f"Region erneut anfragen."
            ),
        ]

    ctx = StrategyContext(
        municipality=municipality,
        canton=canton,
        canton_name=canton_name,
        yoy_change_percent=yoy,
        vacancy_rate_percent=vacancy,
        property_type_de_plural=PROPERTY_TYPE_DE_PLURAL[property_type],
        is_fallback=is_fallback,
    )
    return ctx, data_sources


async def get_acquisition_email_context(
    zip_code: str,
    property_type: PropertyType,
    target_audience: TargetAudience,
) -> AcquisitionEmailContext:
    """Liefert strukturierten Kontext fuer eine Akquise-Mail.

    Der LLM kombiniert die Daten anschliessend mit dem Stil/Signatur
    des Maklers zu einem fertigen Mail-Text. Der Mail-Text wird NICHT
    von diesem Tool generiert.

    Args:
        zip_code: 4-stellige Schweizer PLZ. Bei unbekannter PLZ wird
            graceful auf nationale Mittelwerte zurueckgefallen.
        property_type: "apartment" | "house" | "land" - bestimmt die
            deutsche Pluralform in den Talking Points.
        target_audience: "potential_seller" oder "potential_buyer" -
            entscheidet ueber Strategie + Tone:
              - SELLER: Wertsteigerung, Verkaeufermarkt, kostenlose Bewertung
              - BUYER: enges Angebot, Off-market-Pipeline, Begleitung

    Returns:
        AcquisitionEmailContext mit:
          - region_name, canton, target_audience (echo)
          - market_summary: 1-2 Saetze fuer den Mail-Eintieg
          - trend_data: yoy_change_percent + trend_direction + data_period
          - talking_points: 4-6 strategische Punkte
          - personalization_hints: 4-5 generische Personalisierungs-Hinweise
          - suggested_subject_lines: 2-3 Mail-Betreff-Vorschlaege
          - data_sources: Quellenangabe(n)
          - disclaimer: revDSG/UWG-Hinweis

    Raises:
        pydantic.ValidationError: Bei ungueltigem target_audience oder
            property_type. Eine ungueltige PLZ ist KEIN Fehler -
            das Tool liefert in dem Fall nationale Mittelwerte.
    """
    # Pydantic-Validierung: ungueltige Werte -> pydantic.ValidationError.
    target_audience = _TARGET_AUDIENCE_VALIDATOR.validate_python(target_audience)
    property_type = _PROPERTY_TYPE_VALIDATOR.validate_python(property_type)

    ctx, data_sources = _resolve_context(zip_code, property_type)
    payload = build_payload(target_audience, ctx)

    yoy = ctx["yoy_change_percent"]

    return AcquisitionEmailContext(
        region_name=ctx["municipality"],
        canton=ctx["canton"],
        target_audience=target_audience,
        market_summary=payload["market_summary"],
        trend_data=TrendData(
            yoy_change_percent=yoy,
            trend_direction=_trend_direction(yoy),
            data_period=_DATA_PERIOD,
        ),
        talking_points=payload["talking_points"],
        personalization_hints=payload["personalization_hints"],
        suggested_subject_lines=payload["suggested_subject_lines"],
        data_sources=data_sources,
        disclaimer=ACQUISITION_DISCLAIMER,
    )


__all__ = [
    "AcquisitionEmailContext",
    "TargetAudience",
    "TrendData",
    "TrendDirection",
    "get_acquisition_email_context",
]
