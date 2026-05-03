# Checklist: Go Public

Was muss erledigt sein BEVOR das Repo von Private auf Public umgestellt wird.

## Code-Qualitaet
- [ ] Alle 3 MVP-Tools implementiert und getestet
- [ ] Tests laufen gruen (pytest)
- [ ] mypy --strict ohne Fehler
- [ ] ruff check ohne Fehler
- [ ] Min 1 happy + 1 error path Test pro Tool
- [ ] Dockerfile baut erfolgreich
- [ ] Lokaler Test: Container startet und antwortet auf /sse

## Security
- [ ] Git History auf Secrets gescannt (`gitleaks detect` oder GitHub Secret Scan)
- [ ] `.env` ist in `.gitignore` (verifiziert)
- [ ] Keine Service-Account-JSONs im Repo (nur WIF)
- [ ] Keine API-Keys in Code oder Tests
- [ ] Dependencies auditiert (`pip-audit` oder GitHub Dependabot Alerts gecheckt)

## Lizenz & Legal
- [ ] LICENSE entschieden (Optionen: MIT, Apache-2.0, AGPL-3.0)
- [ ] Lizenzen aller Datenquellen geprueft + im README erwaehnt
  - opendata.swiss: meist CC-BY oder Public Domain - Quellenangabe noetig
  - BFS: Quellenangabe Pflicht
  - OSM Nominatim: ODbL - Attribution noetig + Usage Policy einhalten
- [ ] Disclaimer im README ("keine professionelle Schaetzung")
- [ ] Datenschutz-Hinweis falls Logs personenbezogene Daten enthalten koennten
- [ ] nDSG-Check: Wo werden Daten verarbeitet? (Cloud Run europe-west6 = CH ✓)

## Dokumentation
- [ ] README polished (Tippos, Screenshots, Beispiele)
- [ ] Demo-Video oder mind. 3 Screenshots (Claude Desktop in Action)
- [ ] CONTRIBUTING.md? (optional, aber sinnvoll)
- [ ] Beispiel-Prompts fuer jedes Tool dokumentiert
- [ ] Endpoint-URL nach Cloud Run Deploy ins README

## Branding & Marketing
- [ ] Branding entschieden (RE/MAX Co-Branding oder generisch?)
- [ ] Repo-Description + Topics auf GitHub gesetzt
- [ ] Vater hat ja gesagt
- [ ] (Optional) Submission an https://github.com/punkpeye/awesome-mcp-servers
- [ ] (Optional) Post auf LinkedIn / Schweizer Makler-Communities

## Infra
- [ ] Cloud Run Service laeuft + ist reachable
- [ ] Custom Domain konfiguriert (optional, z.B. `mcp.swissbroker.ch`)
- [ ] Monitoring/Alerting fuer Cloud Run aufgesetzt
- [ ] Cost-Cap auf Cloud Run gesetzt (z.B. max instances = 5)
- [ ] Rate-Limiting ueberlegt (oeffentlicher Endpoint!)

## Final Check
- [ ] Frische Person hat das README gelesen und verstanden was es tut
- [ ] In Claude Desktop selbst getestet mit allen 3 Tools
- [ ] Alle TODOs im Code adressiert oder bewusst dokumentiert
