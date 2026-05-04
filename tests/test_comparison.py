"""Tests fuer Tool 4: compare_locations.

Cases: klassischer Zug-vs-Luzern Steuer-Trade-off, 3-Way Vergleich,
Validation (zu wenig / zu viele PLZ), unbekannte PLZ, Sieger-Logik
und Delta-Linguistik.
"""

from __future__ import annotations

import pytest

from src.tools.comparison import compare_locations
from src.utils.swiss_zip import UnknownZipError


@pytest.mark.asyncio
async def test_zug_vs_luzern_classic_tax_tradeoff() -> None:
    """Der Klassiker: Zug guenstiger steuerlich, Luzern guenstiger Miete."""
    r = await compare_locations(["6300", "6003"])

    assert len(r["locations"]) == 2
    assert {loc["municipality"] for loc in r["locations"]} == {"Zug", "Luzern"}

    # Sieger
    assert r["winners"]["lowest_tax_multiplier"] == "6300"
    assert r["winners"]["lowest_rent"] == "6003"
    assert r["winners"]["highest_income"] == "6300"

    # Tax-Delta in Maklersprache
    tax_delta = next(d for d in r["deltas"] if d["dimension"] == "tax_multiplier")
    assert "Zug" in tax_delta["delta_text"]
    assert "steueroptimaler" in tax_delta["delta_text"]
    # Savings-pct sollte ~69% sein (1.75 -> 0.55)
    assert 60.0 < tax_delta["pct_diff"] < 75.0

    # Rent-Delta
    rent_delta = next(d for d in r["deltas"] if d["dimension"] == "median_rent_chf_per_m2")
    assert "Luzern" in rent_delta["delta_text"]
    assert "guenstiger bei der Miete" in rent_delta["delta_text"]

    # Vacancy: neutrales Framing - "engerer Wohnungsmarkt" statt "guenstiger"
    vac_delta = next(d for d in r["deltas"] if d["dimension"] == "vacancy_rate_percent")
    assert "engeren Wohnungsmarkt" in vac_delta["delta_text"]
    assert "guenstiger" not in vac_delta["delta_text"]

    # Narrative startet mit dem staerksten Delta (Tax bei 69%)
    assert "Zug" in r["narrative_summary"]
    assert "steueroptimaler" in r["narrative_summary"]
    assert "Trade-off" in r["narrative_summary"] or "Fazit" in r["narrative_summary"]

    # Quellen + Disclaimer
    assert r["data_sources"]
    assert r["disclaimer"]


@pytest.mark.asyncio
async def test_three_way_comparison() -> None:
    """Zug vs Luzern vs Sarnen - 3-Way."""
    r = await compare_locations(["6300", "6003", "6060"])

    assert len(r["locations"]) == 3
    assert r["winners"]["lowest_tax_multiplier"] == "6300"  # Zug guenstigster
    # Highest income = Zug (110k) deutlich vor LU/OW
    assert r["winners"]["highest_income"] == "6300"
    # Es muss mindestens ein Delta pro numerische Dimension geben
    dims = {d["dimension"] for d in r["deltas"]}
    assert "tax_multiplier" in dims
    assert "median_rent_chf_per_m2" in dims
    assert "median_household_income_chf" in dims


@pytest.mark.asyncio
async def test_validates_min_locations() -> None:
    """Eine PLZ ist kein Vergleich."""
    with pytest.raises(ValueError, match="2-5"):
        await compare_locations(["6060"])


@pytest.mark.asyncio
async def test_validates_max_locations() -> None:
    """Mehr als 5 PLZ -> harte Abweisung (ist dann eine andere Use-Case-Klasse)."""
    with pytest.raises(ValueError, match="2-5"):
        await compare_locations(["6300", "6003", "6060", "8001", "1003", "4001"])


@pytest.mark.asyncio
async def test_unknown_zip_raises() -> None:
    """Mindestens eine PLZ unbekannt -> UnknownZipError, kein partial."""
    with pytest.raises(UnknownZipError):
        await compare_locations(["6300", "0000"])


@pytest.mark.asyncio
async def test_identical_zips_have_no_deltas() -> None:
    """Same canton/zip-overlap -> Deltas leer oder vergleichbar."""
    r = await compare_locations(["8001", "8002"])
    # Beide Zuerich, gleicher Kanton -> kantonale Werte identisch.
    # Tax-Multiplier ist auch beide 1.19 (ZIP-Override) -> kein Delta.
    tax_deltas = [d for d in r["deltas"] if d["dimension"] == "tax_multiplier"]
    assert tax_deltas == []  # gleicher Wert, kein Delta


@pytest.mark.asyncio
async def test_delta_pct_is_always_non_negative() -> None:
    """Saubere Linguistik: pct_diff ist immer >= 0 (Vorzeichen ist im Text)."""
    r = await compare_locations(["6300", "6003"])
    for d in r["deltas"]:
        assert d["pct_diff"] >= 0
        assert d["pct_diff"] <= 200  # sanity: kein Aufblaehungs-Bug


@pytest.mark.asyncio
async def test_swiss_apostrophe_in_income_format() -> None:
    """Schweizer Tausendertrennzeichen sind Apostrophe, keine Kommas."""
    r = await compare_locations(["6300", "6003"])
    income_delta = next(
        d for d in r["deltas"] if d["dimension"] == "median_household_income_chf"
    )
    # 110'000 statt 110,000
    assert "110'000" in income_delta["delta_text"]
    assert "110,000" not in income_delta["delta_text"]
