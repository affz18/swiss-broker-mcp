"""Tests fuer Tool 3: get_neighborhood_profile.

Happy paths fuer Sarnen (Vater-Demo + Spec-Beispiel), Zuerich, Zug,
plus error path fuer unbekannte PLZ. Cross-checks zwischen
gemeindespezifischen vs. kantonalen Werten.
"""

from __future__ import annotations

import pytest

from src.tools.neighborhood import get_neighborhood_profile
from src.utils.swiss_zip import UnknownZipError


@pytest.mark.asyncio
async def test_happy_sarnen_spec_example() -> None:
    """Sarnen 6060 - laeuft den Spec-Beispiel-Pfad ab."""
    p = await get_neighborhood_profile(zip_code="6060")

    # Lokal-Identitaet
    assert p["zip_code"] == "6060"
    assert p["municipality"] == "Sarnen"
    assert p["canton"] == "Obwalden"
    assert p["canton_code"] == "OW"

    # Population (Spec-Beispiel: 10'281; wir erlauben Approximation)
    assert 9_000 < p["population"] < 12_000

    # Steuern: Sarnen hat ZIP-Override 2.95 (matched Spec exakt)
    assert p["tax_multiplier"] == 2.95
    assert p["tax_rank_canton"] == "guenstig"
    assert "Gemeindespezifisch" in p["tax_multiplier_note"]

    # Markt-Daten kantonal
    assert p["vacancy_rate_percent"] == pytest.approx(0.8)
    assert 14.0 < p["median_rent_chf_per_m2"] < 18.0

    # Infrastruktur: Sarnen >5k Einwohner -> Primar + Sekundar
    assert "Primarschule" in p["infrastructure"]["schools"]
    assert "Sekundarschule" in p["infrastructure"]["schools"]
    # Kein Gymnasium-Eintrag (Sarnen <30k)
    assert not any("Gymnasium" in s for s in p["infrastructure"]["schools"])
    # Highway fuer MVP None
    assert p["infrastructure"]["highway_access_km"] is None
    # OeV-Descriptor fuer 10k Gemeinde
    assert "OeV" in p["infrastructure"]["public_transport"]

    # Demografie - faktisch, kein subjektives Bracket
    demo = p["demographics"]
    assert isinstance(demo["avg_age"], float)
    assert isinstance(demo["avg_household_size"], float)
    assert isinstance(demo["median_household_income_chf"], int)
    # OW Median ist niedriger als CH-Median -> "unter"
    assert "unter" in demo["income_context"]
    assert "Schweizer Median" in demo["income_context"]

    # Quellen + Disclaimer
    assert any("BFS" in src for src in p["data_sources"])
    assert any("ESTV" in src for src in p["data_sources"])
    assert any("Steuerperiode 2025" in src for src in p["data_sources"])
    assert p["disclaimer"]


@pytest.mark.asyncio
async def test_happy_zuerich() -> None:
    """Zuerich 8001 - grosse Stadt, mittlerer Tax-Rang, hohes Median-Einkommen."""
    p = await get_neighborhood_profile(zip_code="8001")

    assert p["municipality"] == "Zuerich"
    assert p["canton"] == "Zuerich"
    assert p["canton_code"] == "ZH"
    assert p["population"] > 100_000
    assert p["tax_rank_canton"] == "mittel"
    assert p["tax_multiplier"] == 1.19  # ZIP-Override
    # Stadt mit >100k Einwohner -> "Sehr gute OeV-Anbindung"
    assert "Sehr gute" in p["infrastructure"]["public_transport"]
    # Schulen: Primar + Sekundar + Gymnasium (>=30k)
    assert "Gymnasium / Mittelschule" in p["infrastructure"]["schools"]

    # Income: ZH (~95k) > CH-Median (82k) -> "ueber"
    assert "ueber" in p["demographics"]["income_context"]


@pytest.mark.asyncio
async def test_happy_zug() -> None:
    """Zug 6300 - guenstigster Steuer-Rang, hoechstes Median-Einkommen."""
    p = await get_neighborhood_profile(zip_code="6300")

    assert p["municipality"] == "Zug"
    assert p["canton_code"] == "ZG"
    assert p["tax_rank_canton"] == "guenstig"
    # ZG Median-Einkommen ~110k - sollte deutlich ueber CH-Median liegen
    assert p["demographics"]["median_household_income_chf"] >= 100_000
    assert "ueber" in p["demographics"]["income_context"]
    # ZG hat den hoechsten Median-Mietpreis
    assert p["median_rent_chf_per_m2"] > 20.0


@pytest.mark.asyncio
async def test_unknown_zip_raises() -> None:
    """Unbekannte PLZ -> harter UnknownZipError (kein Fallback)."""
    with pytest.raises(UnknownZipError, match="0000"):
        await get_neighborhood_profile(zip_code="0000")


@pytest.mark.asyncio
async def test_tax_rank_consistency() -> None:
    """Cross-Check: ZG guenstig, BE teuer, ZH mittel."""
    zg = await get_neighborhood_profile(zip_code="6300")
    be = await get_neighborhood_profile(zip_code="3000")
    zh = await get_neighborhood_profile(zip_code="8001")

    assert zg["tax_rank_canton"] == "guenstig"
    assert be["tax_rank_canton"] == "teuer"
    assert zh["tax_rank_canton"] == "mittel"


@pytest.mark.asyncio
async def test_population_drives_school_descriptor() -> None:
    """Kleine Gemeinde -> nur Primarschule. Grosse Gemeinde -> mit Gymnasium."""
    appenzell = await get_neighborhood_profile(zip_code="9050")  # 6k pop
    zuerich = await get_neighborhood_profile(zip_code="8001")

    # Appenzell: Primarschule + Sekundarschule (>=5k), kein Gymnasium (<30k)
    assert "Primarschule" in appenzell["infrastructure"]["schools"]
    assert "Sekundarschule" in appenzell["infrastructure"]["schools"]
    assert not any("Gymnasium" in s for s in appenzell["infrastructure"]["schools"])

    # Zuerich: alle drei Schulstufen
    assert "Gymnasium / Mittelschule" in zuerich["infrastructure"]["schools"]
