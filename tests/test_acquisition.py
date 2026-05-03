"""Tests fuer Tool 2: get_acquisition_email_context.

Deckt happy paths fuer SELLER + BUYER, graceful fallback bei unbekannter
PLZ und Pydantic-Validierung von target_audience ab.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.tools.acquisition import get_acquisition_email_context


@pytest.mark.asyncio
async def test_happy_seller_luzern() -> None:
    """SELLER Case: 6003 Luzern, Eigentumswohnung."""
    result = await get_acquisition_email_context(
        zip_code="6003",
        property_type="apartment",
        target_audience="potential_seller",
    )

    assert result["region_name"] == "Luzern"
    assert result["canton"] == "LU"
    assert result["target_audience"] == "potential_seller"

    # Seller-spezifischer Wortlaut
    assert "verkaeuferfreundlich" in " ".join(result["talking_points"])
    assert "Wertsteigerung" in result["market_summary"] or any(
        "Verkaeufermarkt" in tp or "verkaeuferfreundlich" in tp
        for tp in result["talking_points"]
    )

    # 4-6 Talking Points laut Spec
    assert 4 <= len(result["talking_points"]) <= 6
    # 3-5 Personalization Hints
    assert 3 <= len(result["personalization_hints"]) <= 5
    # 2-3 Subject Lines
    assert 2 <= len(result["suggested_subject_lines"]) <= 3

    # Trend-Daten
    assert isinstance(result["trend_data"]["yoy_change_percent"], float)
    assert result["trend_data"]["trend_direction"] in ("rising", "falling", "stable")
    assert "Q4" in result["trend_data"]["data_period"] or "12-Monats" in (
        result["trend_data"]["data_period"]
    )

    # Quellen + Disclaimer
    assert any("BFS" in src for src in result["data_sources"])
    assert result["disclaimer"]
    assert "UWG" in result["disclaimer"] or "DSG" in result["disclaimer"]


@pytest.mark.asyncio
async def test_happy_buyer_zuerich() -> None:
    """BUYER Case: 8002 Zuerich (8003 not in table, using 8002)."""
    result = await get_acquisition_email_context(
        zip_code="8002",
        property_type="apartment",
        target_audience="potential_buyer",
    )

    assert result["region_name"] == "Zuerich"
    assert result["canton"] == "ZH"
    assert result["target_audience"] == "potential_buyer"

    joined_tps = " ".join(result["talking_points"])
    # Buyer-spezifische Begriffe
    assert "Off-market" in joined_tps or "off-market" in joined_tps.lower()
    assert "Leerstand" in joined_tps or "Angebot" in joined_tps

    # Subject Lines sollten Buyer-Tone haben
    joined_subj = " ".join(result["suggested_subject_lines"])
    assert "suchen" in joined_subj.lower() or "Off-market" in joined_subj


@pytest.mark.asyncio
async def test_happy_seller_sarnen_vater_demo() -> None:
    """Vater-Demo: Sarnen Verkaeufer-Akquise. Sanity-Check des Outputs."""
    result = await get_acquisition_email_context(
        zip_code="6060",
        property_type="apartment",
        target_audience="potential_seller",
    )

    assert result["region_name"] == "Sarnen"
    assert result["canton"] == "OW"
    # Obwalden ist im Trend gestiegen
    assert result["trend_data"]["yoy_change_percent"] > 0
    assert result["trend_data"]["trend_direction"] == "rising"
    # Sarnen muss in mindestens einer Subject Line vorkommen
    assert any("Sarnen" in s for s in result["suggested_subject_lines"])
    # Property-Type Pluralform (Eigentumswohnungen) muss in Talking Points sein
    assert any(
        "Eigentumswohnungen" in tp for tp in result["talking_points"]
    )


@pytest.mark.asyncio
async def test_unknown_zip_graceful_fallback() -> None:
    """PLZ nicht in Tabelle -> nationale Mittelwerte + transparenter Hinweis."""
    result = await get_acquisition_email_context(
        zip_code="0000",
        property_type="house",
        target_audience="potential_seller",
    )

    # Kein Crash, valide Struktur
    assert result["canton"] == "CH"
    assert result["region_name"] == "der Schweiz"
    # Trend-Daten = nationaler Default
    assert result["trend_data"]["yoy_change_percent"] == pytest.approx(3.0)
    # Hinweis auf Fallback in data_sources
    assert any(
        "0000" in src and "nicht" in src.lower() for src in result["data_sources"]
    )
    # Talking Points & Subject Lines wurden trotzdem gebaut
    assert result["talking_points"]
    assert result["suggested_subject_lines"]


@pytest.mark.asyncio
async def test_invalid_target_audience_pydantic_error() -> None:
    """Ungueltiges target_audience -> pydantic.ValidationError."""
    with pytest.raises(ValidationError):
        await get_acquisition_email_context(
            zip_code="6060",
            property_type="apartment",
            target_audience="random_person",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_invalid_property_type_pydantic_error() -> None:
    """Bonus: ungueltiges property_type -> pydantic.ValidationError."""
    with pytest.raises(ValidationError):
        await get_acquisition_email_context(
            zip_code="6060",
            property_type="castle",  # type: ignore[arg-type]
            target_audience="potential_seller",
        )
