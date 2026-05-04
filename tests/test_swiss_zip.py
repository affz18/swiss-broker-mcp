"""Tests fuer die vollstaendige Schweizer PLZ-Tabelle.

Verifiziert dass die JSON-Resource korrekt geladen wird, alle 26 Kantone
abgedeckt sind und die wichtigsten PLZ aus dem RE/MAX-Vater-Demo + den
existierenden Tools resolven.
"""

from __future__ import annotations

import pytest

from src.utils.swiss_zip import (
    CANTONS,
    UnknownZipError,
    is_known_zip,
    lookup_zip,
    total_zip_count,
)


def test_table_has_full_coverage() -> None:
    """Mindestens 3000 PLZ und alle 26 Kantone."""
    assert total_zip_count() >= 3000
    assert len(CANTONS) == 26


def test_lookup_known_zips() -> None:
    """Spec-Beispiele aus den Tools."""
    sarnen = lookup_zip("6060")
    assert sarnen["municipality"] == "Sarnen"
    assert sarnen["canton"] == "OW"
    assert sarnen["canton_name"] == "Obwalden"

    zh = lookup_zip("8001")
    assert zh["municipality"] == "Zuerich"
    assert zh["canton"] == "ZH"


@pytest.mark.parametrize(
    "zip_code,expected_canton",
    [
        # PLZ die vor v0.2 NICHT in der ~60er-Tabelle waren
        ("8003", "ZH"),  # Zuerich (Wiedikon)
        ("8005", "ZH"),  # Zuerich (Industriequartier)
        ("8048", "ZH"),  # Zuerich (Albisrieden)
        ("4502", "SO"),  # Solothurn-Vorort
        ("1004", "VD"),  # Lausanne
        ("3007", "BE"),  # Bern (Mattenhof)
        ("8302", "ZH"),  # Kloten
        ("6010", "LU"),  # Kriens
        ("4123", "BL"),  # Allschwil
        ("9000", "SG"),  # St. Gallen Stadt
    ],
)
def test_previously_uncovered_zips(zip_code: str, expected_canton: str) -> None:
    """Stichproben aus dem long tail der Schweizer PLZ - vorher Fehler, jetzt OK."""
    entry = lookup_zip(zip_code)
    assert entry["canton"] == expected_canton
    assert entry["municipality"]  # nicht leer
    assert is_known_zip(zip_code)


def test_unknown_zip_raises_with_helpful_message() -> None:
    with pytest.raises(UnknownZipError, match="0000"):
        lookup_zip("0000")


def test_each_canton_has_at_least_one_zip() -> None:
    """Sanity: alle 26 Kantone tauchen in der Tabelle auf."""
    from src.utils.swiss_zip import _ZIP_TABLE

    cantons_in_table = {canton for _, canton in _ZIP_TABLE.values()}
    assert cantons_in_table == set(CANTONS.keys())


def test_no_umlauts_in_table_values() -> None:
    """ASCII-only Konvention: keine Umlaute in Gemeindenamen."""
    from src.utils.swiss_zip import _ZIP_TABLE

    forbidden = "äöüÄÖÜßéèêàâîôûç"
    for zip_code, (municipality, _) in _ZIP_TABLE.items():
        for char in forbidden:
            assert char not in municipality, (
                f"PLZ {zip_code}: {municipality!r} enthaelt nicht-ASCII-Zeichen"
            )


def test_lookup_returns_typed_dict_shape() -> None:
    entry = lookup_zip("6060")
    assert set(entry.keys()) == {"zip_code", "municipality", "canton", "canton_name"}
