# GCP Setup fuer Swiss Broker MCP

Einmalige Einrichtung deines GCP-Projekts, damit der GitHub-Actions-
Deploy-Workflow (`.github/workflows/deploy.yml`) den Server nach Cloud
Run pushen kann. **Workload Identity Federation** statt JSON-Service-
Account-Key - sicherer, kein Secret-Rotations-Aufwand.

> Dauer: ~10 Minuten. Du brauchst die `gcloud` CLI lokal **oder** den
> GCP Cloud Shell. Alle Befehle sind copy-paste-ready - die Variablen
> oben in der Shell setzen, dann der Rest sequenziell.

---

## 0. Variablen setzen

```bash
# Dein GCP-Projekt
export GCP_PROJECT_ID="dein-projekt-id"

# Region: europe-west6 = Zuerich (nDSG-konform)
export GCP_REGION="europe-west6"

# Service-Konvention - bitte nicht aendern, sonst muessen die
# deploy.yml Werte ebenfalls angepasst werden.
export ARTIFACT_REPO="swiss-broker-mcp"
export CLOUD_RUN_SERVICE="swiss-broker-mcp"
export DEPLOY_SA="swiss-broker-mcp-deployer"
export WIF_POOL="github-pool"
export WIF_PROVIDER="github-provider"

# Dein GitHub-Repo (owner/repo)
export GITHUB_REPO="affz18/swiss-broker-mcp"
```

```bash
gcloud config set project "$GCP_PROJECT_ID"
```

---

## 1. APIs aktivieren

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  sts.googleapis.com
```

---

## 2. Artifact Registry Repository

Container-Images leben hier (eine Region, gleicher Standort wie
Cloud Run, vermeidet Cross-Region-Traffic-Kosten).

```bash
gcloud artifacts repositories create "$ARTIFACT_REPO" \
  --repository-format=docker \
  --location="$GCP_REGION" \
  --description="Swiss Broker MCP container images"
```

Pruefen:

```bash
gcloud artifacts repositories list --location="$GCP_REGION"
```

---

## 3. Service Account fuer den Deploy

```bash
gcloud iam service-accounts create "$DEPLOY_SA" \
  --display-name="Swiss Broker MCP - GitHub Actions Deployer"
```

Die volle E-Mail merken (wird spaeter als GitHub Secret gebraucht):

```bash
export DEPLOY_SA_EMAIL="${DEPLOY_SA}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
echo "Service Account: $DEPLOY_SA_EMAIL"
```

### Rollen fuer den Service Account

Drei minimale Rollen, kein Owner / Editor:

```bash
# 1) Cloud Run deploy + manage
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
  --role="roles/run.admin"

# 2) Service Account User (damit Cloud Run den runtime-SA nutzen darf)
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# 3) Push in Artifact Registry
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
  --role="roles/artifactregistry.writer"
```

---

## 4. Workload Identity Federation (WIF)

GitHub-Actions authentifiziert sich via OIDC-Token statt JSON-Key.
Sicher + ohne Secret-Rotation.

### 4a. Pool

```bash
gcloud iam workload-identity-pools create "$WIF_POOL" \
  --location=global \
  --display-name="GitHub Actions Pool"
```

### 4b. Provider (GitHub-OIDC) mit Repo-Restriction

Wichtig: `attribute-condition` schraenkt ein, dass nur Tokens unseres
Repos akzeptiert werden. Ohne diese Bedingung koennte JEDES GitHub-
Repo unsere GCP-Ressourcen ansprechen.

```bash
gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
  --location=global \
  --workload-identity-pool="$WIF_POOL" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 4c. Provider mit dem Service Account verknuepfen

```bash
export GCP_PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/${GITHUB_REPO}"
```

### 4d. Provider Resource Name auslesen

Wird gleich als GitHub Secret gebraucht:

```bash
export WIF_PROVIDER_RESOURCE="projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"
echo "WIF Provider: $WIF_PROVIDER_RESOURCE"
```

---

## 5. GitHub Secrets setzen

In deinem GitHub-Repo unter **Settings -> Secrets and variables ->
Actions -> New repository secret** drei Secrets anlegen:

| Secret | Wert (entspricht Variable oben) |
|--------|---------------------------------|
| `GCP_PROJECT_ID` | `$GCP_PROJECT_ID` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `$WIF_PROVIDER_RESOURCE` |
| `GCP_SERVICE_ACCOUNT` | `$DEPLOY_SA_EMAIL` |

Schnell-Check via CLI (zeigt die Werte an, die du eintragen musst):

```bash
echo "GCP_PROJECT_ID=$GCP_PROJECT_ID"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=$WIF_PROVIDER_RESOURCE"
echo "GCP_SERVICE_ACCOUNT=$DEPLOY_SA_EMAIL"
```

Falls du `gh` CLI installiert hast, kannst du sie auch direkt setzen:

```bash
gh secret set GCP_PROJECT_ID --body "$GCP_PROJECT_ID"
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER_RESOURCE"
gh secret set GCP_SERVICE_ACCOUNT --body "$DEPLOY_SA_EMAIL"
```

---

## 6. Deploy testen

Push auf `main` -> der Workflow `.github/workflows/deploy.yml` startet
automatisch. Manuell triggerbar via GitHub UI ("Actions -> deploy ->
Run workflow") oder:

```bash
gh workflow run deploy.yml
```

Nach erfolgreichem Deploy:

```bash
gcloud run services describe "$CLOUD_RUN_SERVICE" \
  --region="$GCP_REGION" \
  --format='value(status.url)'
```

Den ausgegebenen URL in `claude_desktop_config.json` eintragen
(Endpoint ist `<URL>/mcp`):

```json
{
  "mcpServers": {
    "swiss-broker": {
      "url": "https://swiss-broker-mcp-<HASH>-oa.a.run.app/mcp"
    }
  }
}
```

Smoke-Test:

```bash
curl "$(gcloud run services describe "$CLOUD_RUN_SERVICE" --region="$GCP_REGION" --format='value(status.url)')/health"
# -> {"status":"ok"}
```

---

## 7. Cost Cap (empfohlen)

Cloud Run skaliert auto auf 0 wenn keine Anfragen reinkommen. Aber:
ein abusiver Client koennte trotzdem Kosten erzeugen. Setze ein
Hard-Cap via Billing-Budget:

GCP Console -> Billing -> Budgets & alerts -> "Create budget" ->
Threshold 50 CHF/Monat, Alert bei 50%/90%/100%.

`max-instances=5` aus `deploy.yml` ist bereits gesetzt; das limitiert
die parallele Last (bei 512 MiB / 1 vCPU pro Instance ein vernuenftiger
Default fuer einen MVP).

---

## Troubleshooting

**`PERMISSION_DENIED: Permission iam.serviceAccounts.getAccessToken denied`**
-> `roles/iam.workloadIdentityUser` Binding aus Schritt 4c fehlt oder
das `attribute.repository` matcht nicht (case-sensitive!).

**`The principal must be authorized for ... artifactregistry.repositories.uploadArtifacts`**
-> `roles/artifactregistry.writer` aus Schritt 3 fehlt fuer den Service
Account.

**`Cloud Run service is reachable, but /mcp returns 404`**
-> Pruefen ob `mcp.run(transport="http", ...)` (nicht "sse" oder "stdio")
in `src/server.py` gesetzt ist. Endpoint ist /mcp bei "http"-Transport,
/sse bei "sse"-Transport.
