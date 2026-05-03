"""Tests fuer Tool 1: valuate_property.

Min 1 happy + 1 error path + Sanity-Checks der Modifikatoren-Logik.
Keine HTTP-Mocks noetig (Tool nutzt aktuell nur embedded Daten).
"""

from __future__ import annotations

import pytest

from src.tools.valuation import valuate_property
from src.utils.swiss_zip import UnknownZipError


@pytest.mark.asyncio
async def test_happy_path_sarnen_apartment() -> None:
    """Original-Beispiel aus der Spec: 4.5-Zi Wohnung in 6060 Sarnen, 120m2."""
    result = await valuate_property(
        zip_code="6060",
        property_type="apartment",
        size_m2=120,
        rooms=4.5,
        condition="good",
        year_built=2015,
    )

    # Strukturelle Asserts (Output-Schema)
    assert isinstance(result["estimated_value_chf"], int)
    assert result["estimated_value_chf"] > 0
    assert result["price_range_chf"]["min"] < result["estimated_value_chf"]
    assert result["price_range_chf"]["max"] > result["estimated_value_chf"]
    assert result["price_per_m2"] > 0
    assert "Sarnen" in result["comparable_region"]
    assert "Obwalden" in result["comparable_region"]
    assert result["confidence"] in ("high", "medium", "low")
    assert result["data_sources"]
    assert "BFS" in result["data_sources"][0]
    assert result["disclaimer"]
    assert result["broker_notes"]
    assert "12 Monaten" in result["market_context"]

    # Plausibilitaet: OW Apt @ 7500 base, year_built 2015 -> +5%, condition good -> 1.0
    # => price_per_m2 ~ 7875 -> *120 = ~945k. Range +-12%.
    assert 800_000 < result["estimated_value_chf"] < 1_100_000


@pytest.mark.asyncio
async def test_unknown_zip_raises() -> None:
    with pytest.raises(UnknownZipError, match="0000"):
        await valuate_property(
            zip_code="0000",
            property_type="apartment",
            size_m2=100,
            rooms=4.0,
            condition="good",
        )


@pytest.mark.asyncio
async def test_renovated_higher_than_good_higher_than_needs_work() -> None:
    """Modifikator-Logik: renoviert > gut > sanierungsbeduerftig."""
    common = {
        "zip_code": "6060",
        "property_type": "apartment",
        "size_m2": 120,
        "rooms": 4.5,
    }
    renovated = await valuate_property(**common, condition="renovated")  # type: ignore[arg-type]
    good = await valuate_property(**common, condition="good")  # type: ignore[arg-type]
    needs_work = await valuate_property(**common, condition="needs_work")  # type: ignore[arg-type]

    assert renovated["estimated_value_chf"] > good["estimated_value_chf"]
    assert good["estimated_value_chf"] > needs_work["estimated_value_chf"]


@pytest.mark.asyncio
async def test_invalid_property_type_raises() -> None:
    with pytest.raises(ValueError, match="property_type"):
        await valuate_property(
            zip_code="6060",
            property_type="palace",  # type: ignore[arg-type]
            size_m2=100,
            rooms=4.0,
            condition="good",
        )


@pytest.mark.asyncio
async def test_invalid_size_raises() -> None:
    with pytest.raises(ValueError, match="size_m2"):
        await valuate_property(
            zip_code="6060",
            property_type="apartment",
            size_m2=-5,
            rooms=4.0,
            condition="good",
        )


@pytest.mark.asyncio
async def test_canton_difference_zh_higher_than_ju() -> None:
    """Sanity: Zuerich-Wohnung sollte teurer sein als gleiche im Jura."""
    zh = await valuate_property(
        zip_code="8001",
        property_type="apartment",
        size_m2=100,
        rooms=4.0,
        condition="good",
    )
    ju = await valuate_property(
        zip_code="2800",
        property_type="apartment",
        size_m2=100,
        rooms=4.0,
        condition="good",
    )
    assert zh["estimated_value_chf"] > ju["estimated_value_chf"]


@pytest.mark.asyncio
async def test_low_confidence_for_extreme_size() -> None:
    """Mini-Wohnung 10m2 -> low confidence."""
    result = await valuate_property(
        zip_code="8001",
        property_type="apartment",
        size_m2=10,
        rooms=1.0,
        condition="good",
    )
    assert result["confidence"] == "low"
