"""Zentrale Disclaimer-Texte (DRY).

Werden von mehreren Tools im Output mitgeliefert. Aenderungen hier
wirken sich auf alle Tools aus - bewusst zentralisiert, damit Legal-
Updates nicht an mehreren Stellen vergessen werden.
"""

from __future__ import annotations

VALUATION_DISCLAIMER = (
    "Schaetzung basiert auf oeffentlichen Statistiken (BFS, opendata.swiss) "
    "und ersetzt keine professionelle Schaetzung. Fuer rechtsverbindliche "
    "Werte ist eine Vor-Ort-Besichtigung durch einen zertifizierten "
    "Schaetzer erforderlich."
)

VALUATION_BROKER_NOTES = (
    "Fuer eine genaue Bewertung wird eine Vor-Ort-Besichtigung empfohlen. "
    "Faktoren wie Aussicht, Stockwerk, Nebenkosten, Sanierungsbedarf und "
    "individuelle Ausstattung sind in dieser Schaetzung NICHT beruecksichtigt."
)

ACQUISITION_DISCLAIMER = (
    "Talking Points und Subject Lines sind Vorschlaege auf Basis "
    "regionaler Markt-Annaeherungen. Die finale Mail muss durch den "
    "Makler personalisiert und auf die rechtlichen Anforderungen geprueft "
    "werden (revDSG/nDSG fuer Datenverarbeitung, UWG Art. 3 Abs. 1 lit. o "
    "fuer Massenwerbung, Opt-out-Recht des Empfaengers)."
)
