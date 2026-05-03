# Swiss Broker MCP

> **Schweizer Immobilien-Marktdaten direkt im Chat. Eine Frage statt drei Browser-Tabs.**

Du bist Makler in der Schweiz. Du hast Claude Desktop offen. Du fragst:

> *"Bewerte mir eine 4.5-Zimmer-Wohnung in 6060 Sarnen, 120 m2, Baujahr 2015, gepflegt."*

Und bekommst eine fundierte Schaetzung mit Preisspanne, Vergleichsregion,
Marktkontext, Quellenangabe und Disclaimer - in dem Chat, in dem du
ohnehin schon arbeitest. Kein Comparis-Login, kein Excel mit Steuer-
fuessen, kein BFS-Portal auf einem dritten Tab.

Der Server ruft selbst **keine LLM-API** auf. Er ist eine reine Daten-
Bridge: er liefert deinem Chat-Client strukturierte Schweizer Markt-
daten, die Antwort baut Claude (oder ChatGPT, oder Cursor) bei dir.

---

## Was es macht

Drei MVP-Tools, alle auf oeffentlichen Schweizer Daten (BFS, ESTV).

### 1. `valuate_property` - Immobilien bewerten

> *"Was ist eine 4.5-Zimmer-Wohnung in 6060 Sarnen, 120 m2, Bj. 2015, gepflegt, wert?"*

```json
{
  "estimated_value_chf": 945000,
  "price_range_chf": { "min": 831600, "max": 1058400 },
  "price_per_m2": 7875,
  "comparable_region": "Sarnen + Umgebung Kanton Obwalden",
  "confidence": "medium",
  "market_context": "Preise im Kanton Obwalden sind in den letzten 12 Monaten um 4.2% gestiegen.",
  "broker_notes": "Fuer eine genaue Bewertung wird eine Vor-Ort-Besichtigung empfohlen ...",
  "data_sources": ["BFS Wohnimmobilienpreisindex 2024 (regionale Annaeherung)"],
  "disclaimer": "Schaetzung basiert auf oeffentlichen Statistiken ..."
}
```

### 2. `get_acquisition_email_context` - Akquise-Mail vorbereiten

> *"Schreib eine Akquise-Mail fuer Eigentuemer einer Wohnung in 6003 Luzern."*

Das Tool liefert dir Talking Points, Subject Lines und Personali-
sierungs-Hints. Die fertige Mail schreibt Claude bei dir - mit deinem
Stil, deiner Anrede, deiner Signatur.

```json
{
  "region_name": "Luzern",
  "canton": "LU",
  "target_audience": "potential_seller",
  "market_summary": "Preise im Kanton Luzern sind in den letzten 12 Monaten um 4.2% gestiegen. Verkaeufermarkt: hohe Nachfrage, kurze Verkaufsdauer.",
  "trend_data": { "yoy_change_percent": 4.2, "trend_direction": "rising", "data_period": "..." },
  "talking_points": [
    "Der Markt in Luzern ist aktuell verkaeuferfreundlich.",
    "Preise im Kanton Luzern +4.2% in den letzten 12 Monaten ...",
    "Hohe Nachfrage nach Eigentumswohnungen ...",
    "Eine kostenlose Marktwert-Einschaetzung ist ein unverbindlicher Erstkontakt."
  ],
  "personalization_hints": [
    "Stelle Bezug zu einer aktuellen lokalen Entwicklung her ...",
    "Erwaehne die kantonale Steuerentwicklung als Zeitpunkt-Argument ..."
  ],
  "suggested_subject_lines": [
    "Ihre Immobilie in Luzern: kostenlose Marktwert-Einschaetzung",
    "Luzern: Verkaufspreise +4.2% - was ist Ihre Liegenschaft heute wert?",
    "Kurze Frage zu Ihrer Liegenschaft in Luzern"
  ],
  "disclaimer": "... revDSG/nDSG ... UWG Art. 3 Abs. 1 lit. o ..."
}
```

Asymmetrische Strategie: `target_audience: "potential_seller"` fokussiert
auf Wertsteigerung + kostenlose Bewertung, `"potential_buyer"` auf knappes
Angebot + Off-market-Pipeline.

### 3. `get_neighborhood_profile` - Gemeinde-Profil

> *"Wie ist die Gemeinde 6060? Steuerfuss, Demografie, Mieten?"*

```json
{
  "zip_code": "6060",
  "municipality": "Sarnen",
  "canton": "Obwalden",
  "canton_code": "OW",
  "population": 10300,
  "tax_multiplier": 2.95,
  "tax_rank_canton": "guenstig",
  "tax_multiplier_note": "Gemeindespezifisch (Steuerperiode 2025) ...",
  "vacancy_rate_percent": 0.8,
  "median_rent_chf_per_m2": 16.0,
  "infrastructure": {
    "schools": ["Primarschule", "Sekundarschule"],
    "public_transport": "Gute OeV-Anbindung (Bahn-/S-Bahn-Halt im Ort, lokale Buslinien).",
    "highway_access_km": null
  },
  "demographics": {
    "avg_age": 42.0,
    "avg_household_size": 2.4,
    "median_household_income_chf": 78000,
    "income_context": "Liegt 5% unter dem Schweizer Median (82'000 CHF)."
  },
  "data_sources": ["BFS STATPOP / HABE 2024", "ESTV / kantonale Steuerverwaltungen, Steuerperiode 2025"],
  "disclaimer": "Profil-Daten sind regionale Annaeherungen ..."
}
```

---

## Installation in Claude Desktop

> **Status: Pre-Alpha.** Endpoint-URL folgt nach dem ersten Cloud-Run-Deploy.

Fuege folgendes zu deiner `claude_desktop_config.json` hinzu:

```json
{
  "mcpServers": {
    "swiss-broker": {
      "url": "https://swiss-broker-mcp-<TODO-HASH>-oa.a.run.app/sse"
    }
  }
}
```

Claude Desktop neu starten, fertig. Anleitung fuer Cursor und ChatGPT
folgt sobald die offizielle MCP-Unterstuetzung dieser Clients stabil ist.

---

## Roadmap

### v0.2 (geplant)
- `compare_locations` - zwei oder mehr Gemeinden direkt vergleichen
- `get_expose_context` - Daten fuer Verkaufs-Exposes
- `generate_market_report_data` - strukturierte Markt-Reports
- Live-Anbindung an die BFS pxweb-API (statt embedded Annaeherungen)
- Vollstaendige PLZ-Tabelle (~3000 Eintraege statt aktuell ~60)

### v0.3 (Idee)
- OSM Overpass fuer `highway_access_km` und konkrete OeV-Verbindungen
- Lokale Hooks (Bauprojekte, Schulausbau) ueber kommunale News-Feeds
- i18n: Franzoesisch + Italienisch
- Optionaler Auth-Layer (API-Key) fuer Premium-Features
- Adapter fuer kommerzielle Datenquellen (IAZI / Wuest), sofern Lizenz

---

## Tech Stack

- **Python 3.11+**
- **[FastMCP](https://github.com/jlowin/fastmcp)** - MCP-Server-Framework
- **[Google Cloud Run](https://cloud.google.com/run)** - Hosting in
  `europe-west6` (Zuerich), nDSG-konform, Workload Identity Federation
- `httpx` (async HTTP), `structlog` (JSON-Logs), `pydantic` (Validierung)
- `pytest` + `pytest-asyncio` + `respx`, `mypy --strict`, `ruff`

Deployment via GitHub Actions auf Push nach `main`.

### Benoetigte GitHub Secrets

| Secret | Beschreibung |
|--------|--------------|
| `GCP_PROJECT_ID` | Deine Google Cloud Project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider Resource Name |
| `GCP_SERVICE_ACCOUNT` | Service-Account-E-Mail mit Cloud-Run-Deploy-Permissions |

Wir nutzen **Workload Identity Federation** statt JSON-Keys -
sicherer und ohne manuelle Secret-Rotation.

---

## Datenquellen

Alle Daten stammen aus oeffentlichen Schweizer Quellen. Quellen werden
in jedem Tool-Output transparent unter `data_sources` mitgeliefert.

- **[Bundesamt fuer Statistik (BFS)](https://www.bfs.admin.ch/)**
  Wohnimmobilienpreisindex, Mietpreisstrukturerhebung, STATPOP
  (Bevoelkerung), HABE (Haushaltseinkommen), Leerwohnungszaehlung.
- **[Eidgenoessische Steuerverwaltung (ESTV)](https://www.estv.admin.ch/)**
  Steuerbelastungsmonitor, kantonale Steuerfuesse.
- **[opendata.swiss](https://opendata.swiss/)**
  CKAN-Portal fuer oeffentliche Verwaltungsdaten.
- **[OpenStreetMap / Nominatim](https://nominatim.org/)** (ab v0.3)
  Geocoding und POIs.

Aktuelle MVP-Werte sind plausible Annaeherungen 2024-2025, die im
Code als solche dokumentiert sind. Live-API-Anbindung ist Teil von
v0.2 (siehe Roadmap).

---

## Disclaimer

Alle Schaetzungen und Profile basieren auf oeffentlichen Statistiken
und ersetzen **keine professionelle Bewertung**. Der Server uebernimmt
keine Garantie fuer Aktualitaet oder Vollstaendigkeit der Daten. Fuer
rechtsverbindliche Werte bitte direkt die jeweilige Wohngemeinde,
einen zertifizierten Schaetzer oder die ESTV anfragen.

---

## Status & Lizenz

**Pre-Alpha** - im aktiven Aufbau auf Branch `claude/swiss-broker-mcp-setup-Ayhod`.
Stand der Vorbereitung fuer Public-Release: siehe
[CHECKLIST_GO_PUBLIC.md](./CHECKLIST_GO_PUBLIC.md).

**License:** TBD - wird vor dem Public-Release entschieden.
