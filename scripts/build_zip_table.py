"""Build script: Schweizer PLZ-Tabelle aus zauberware/postal-codes-json-xml-csv.

Erzeugt `src/utils/swiss_zip_data.json` aus dem Dataset
zauberware/postal-codes-json-xml-csv (Quelle: geonames.org).

Die Schweiz hat ~3362 unterschiedliche PLZ und ~2147 Gemeinden. 221 PLZ
ueberschneiden Gemeindegrenzen - in diesen Faellen waehlen wir die
"kanonische" Gemeinde (jene, deren Name dem Ortsnamen entspricht).

Umlaute / franzoesische Akzente werden zu ASCII transliteriert (ue, oe,
ae, ss, e, ...) - gleiche Konvention wie im restlichen Codebase.

Reproduzieren:

    python scripts/build_zip_table.py [INPUT_JSON]

    Default INPUT_JSON: zipcodes.ch.json (entpackt aus
    https://github.com/zauberware/postal-codes-json-xml-csv/raw/master/data/CH.zip)

Output: src/utils/swiss_zip_data.json (sortiert, kompakt).
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

# Schweizerdeutsche Umlaute -> ae/oe/ue (NICHT bare a/o/u, das waere
# falsch ausgesprochen und kantonale Eigennamen sind genormt).
GERMAN_UMLAUT_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
)


def transliterate(s: str) -> str:
    """German umlauts + French/Italian accents -> ASCII."""
    s = s.translate(GERMAN_UMLAUT_MAP)
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def build(input_path: Path, output_path: Path) -> None:
    raw: list[dict[str, Any]] = json.loads(input_path.read_text(encoding="utf-8"))

    # ZIP -> liste der (community, canton, place_matches_community) Kandidaten.
    candidates: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)
    for e in raw:
        zip_code = e["zipcode"]
        community = transliterate(e["community"])
        place = transliterate(e["place"])
        canton = e["state_code"]
        candidates[zip_code].append((community, canton, place == community))

    # Pro ZIP: bevorzugt eine kanonische Gemeinde, sonst die erste alphabetisch.
    table: dict[str, list[str]] = {}
    for zip_code, cs in candidates.items():
        canonical = next((c for c in cs if c[2]), None)
        chosen = canonical or sorted(cs)[0]
        table[zip_code] = [chosen[0], chosen[1]]

    # Sort fuer reproduzierbares Diff.
    sorted_table = dict(sorted(table.items()))

    # Kompakter Output: keine Whitespace zwischen Tokens, aber 1 Eintrag pro Zeile
    # damit Diffs lesbar bleiben.
    lines = ["{"]
    items = list(sorted_table.items())
    for i, (zip_code, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        lines.append(f'  "{zip_code}":["{value[0]}","{value[1]}"]{comma}')
    lines.append("}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Stats
    cantons = sorted({v[1] for v in sorted_table.values()})
    print(f"Wrote {len(sorted_table)} ZIPs to {output_path}")
    print(f"Cantons covered: {len(cantons)} - {cantons}")
    print(f"Output size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ch_data/zipcodes.ch.json")
    output_path = Path(__file__).parent.parent / "src" / "utils" / "swiss_zip_data.json"
    build(input_path, output_path)
