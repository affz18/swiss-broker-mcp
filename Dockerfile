# syntax=docker/dockerfile:1.6

# ----- Stage 1: Builder -----
# Installiert Python-Dependencies in eine virtualenv, damit das Final-
# Image keine Build-Tools/pip-Caches mitschleppen muss.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt ./

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt


# ----- Stage 2: Runtime -----
# Slim image, non-root user, nur das was zur Laufzeit gebraucht wird.
FROM python:3.11-slim

# Non-root User fuer Cloud Run / Security-Best-Practice.
RUN groupadd --system --gid 10001 appuser && \
    useradd --system --uid 10001 --gid appuser --no-create-home appuser

# Virtualenv aus dem Builder uebernehmen.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Source-Code mit korrekten Permissions kopieren.
COPY --chown=appuser:appuser src/ ./src/

USER appuser

# Cloud Run setzt PORT zur Laufzeit; EXPOSE ist nur Doku.
EXPOSE 8080

# Server starten - liest PORT aus env (default 8080).
CMD ["python", "-m", "src.server"]
