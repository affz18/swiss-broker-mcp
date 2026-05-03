# Swiss Broker MCP

> Ein AI Co-Pilot fuer Schweizer Immobilien-Makler. Liefert Schweizer
> Marktdaten direkt in Claude Desktop, ChatGPT oder Cursor.

## Was ist das?

Ein **MCP (Model Context Protocol) Server**, der Schweizer Immobilien-
Marktdaten (BFS, opendata.swiss, OSM) in deinem Chat-Client verfuegbar
macht. Statt zwischen 5 Browser-Tabs zu jonglieren, fragst du einfach:

> "Bewerte mir eine 4.5-Zimmer-Wohnung in 6060 Sarnen, 120 m², Baujahr 2015."

und bekommst eine fundierte Schaetzung mit Quellenangaben - direkt im Chat.

## Warum?

Schweizer Makler verlieren taeglich Stunden mit Routine-Recherche:
- Marktpreise nachschlagen (Wuest&Partner, IAZI, Comparis...)
- Steuerfuss pro Gemeinde recherchieren
- Demografie-Daten zusammensuchen
- Akquise-Mails personalisieren

**Swiss Broker MCP** bringt all das in den Chat-Workflow den du eh schon nutzt.

## Installation in Claude Desktop

> ⚠️ **Status:** Pre-Alpha. Endpoint-URL folgt nach Cloud Run Deploy.

Fuege folgendes zu deiner `claude_desktop_config.json` hinzu:

```json
{
  "mcpServers": {
    "swiss-broker": {
      "url": "https://swiss-broker-mcp-<HASH>-oa.a.run.app/sse"
    }
  }
}
```

(Cursor / ChatGPT Anleitung folgt.)

## Tools (MVP)

### 1. `valuate_property` - Immobilien-Bewertung

Beispiel:
> "Bewerte mir eine 4.5-Zi Wohnung in 6060 Sarnen, 120m², renoviert."

Liefert geschaetzten Wert, Preisspanne, Vergleichsregion, Quellen
und Markt-Kontext.

### 2. `get_acquisition_email_context` - Akquise-Mail-Daten

Beispiel:
> "Schreib eine Akquise-Mail fuer Eigentuemer in 6003 Luzern."

Liefert dem LLM regionale Markt-Insights + Talking Points.
**Den eigentlichen Mail-Text schreibt Claude** - mit deinem Stil,
deiner Anrede, deiner Signatur.

### 3. `get_neighborhood_profile` - Gemeinde-Profil

Beispiel:
> "Wie ist die Gemeinde 6060? Steuerfuss, Demografie, Leerstand?"

Liefert ein vollstaendiges Profil: Steuern, Bevoelkerung, Mieten,
Infrastruktur, Schulen, Verkehrsanbindung.

## Datenquellen

- **[opendata.swiss](https://opendata.swiss/)** - CKAN Open Data Portal des Bundes
- **[BFS](https://www.bfs.admin.ch/)** - Bundesamt fuer Statistik
  (Wohnimmobilienpreisindex, Mietpreisindex, Demografie)
- **[OpenStreetMap Nominatim](https://nominatim.org/)** - Geocoding & POIs
- **Steuerfuss-Daten** - kantonale Open-Data-Portale / ESTV

Alle Daten sind oeffentlich. Der Server ruft KEINE LLM-APIs auf -
er ist eine reine Daten-Bridge.

## Deployment (fuer Self-Hosting)

Der Server ist als Container fuer Google Cloud Run europe-west6 (Zuerich)
ausgelegt - nDSG-konform, da alle Daten in der Schweiz bleiben.

GitHub Actions deployt automatisch bei Push auf `main`.

### Benoetigte GitHub Secrets

| Secret | Beschreibung |
|--------|--------------|
| `GCP_PROJECT_ID` | Deine Google Cloud Project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider Resource Name (`projects/.../providers/...`) |
| `GCP_SERVICE_ACCOUNT` | Service Account E-Mail mit Cloud Run Deploy Permissions |

Wir nutzen **Workload Identity Federation** statt JSON-Keys -
sicherer und ohne Secret-Rotation.

## Roadmap

- [x] MVP: 3 Tools (valuate, acquisition, neighborhood)
- [ ] Tool 4: `compare_locations` - Gemeinden vergleichen
- [ ] Tool 5: `get_expose_context` - Verkaufs-Expose-Daten
- [ ] Tool 6: `generate_market_report_data` - Markt-Reports
- [ ] i18n: Franzoesisch + Italienisch
- [ ] Privat-Daten-Adapter (IAZI/Wuest, sofern Lizenz vorhanden)
- [ ] Auth-Layer (API-Key) fuer Premium-Features

## Disclaimer

Alle Schaetzungen basieren auf oeffentlichen Statistiken und ersetzen
**keine professionelle Schaetzung**. Der Server uebernimmt keine
Garantie fuer Aktualitaet oder Vollstaendigkeit der Daten.

## Entwicklung

Siehe [CHECKLIST_GO_PUBLIC.md](./CHECKLIST_GO_PUBLIC.md) fuer den Stand
vor dem Public-Release.

## Lizenz

TBD (siehe [CHECKLIST_GO_PUBLIC.md](./CHECKLIST_GO_PUBLIC.md)).
