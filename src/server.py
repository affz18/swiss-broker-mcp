"""FastMCP Server Entry Point.

Registriert alle MCP-Tools und startet den Server im Streamable-HTTP-
Transport. MCP-Clients (Claude Desktop, Cursor, ChatGPT) verbinden sich
auf `https://<host>/mcp`.

Zusaetzlich exponiert der Server einen `/health`-Endpoint fuer Cloud-
Run-Probes (Liveness/Readiness): GET /health -> 200 {"status": "ok"}.

Logging: structlog im JSON-Format auf stderr - Cloud Run Logging parst
das automatisch in strukturierte Felder.
"""

from __future__ import annotations

import logging
import os
import sys

import structlog
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.tools.acquisition import get_acquisition_email_context
from src.tools.comparison import compare_locations
from src.tools.neighborhood import get_neighborhood_profile
from src.tools.valuation import valuate_property

# .env lokal laden (Cloud Run injiziert env vars direkt).
load_dotenv()


def _configure_logging() -> None:
    """structlog -> JSON, Output stderr (Cloud Run Convention)."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, log_level, logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


_configure_logging()
log = structlog.get_logger("swiss-broker-mcp")

mcp: FastMCP = FastMCP(
    "swiss-broker-mcp",
    instructions=(
        "Schweizer Immobilien-Marktdaten fuer Makler. Tools liefern "
        "strukturierte Daten + deutsche Texte; das LLM verpackt sie "
        "fuer den Endnutzer (Bewertung, Akquise-Mail, Beratung)."
    ),
)


# --- Tool-Registrierung ---
mcp.tool()(valuate_property)
mcp.tool()(get_acquisition_email_context)
mcp.tool()(get_neighborhood_profile)
mcp.tool()(compare_locations)


# --- Custom HTTP routes (ausserhalb des MCP-Protokolls) ---
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Cloud-Run Health-Probe Endpoint.

    Bewusst minimal: kein Datenbank-Ping, kein externer API-Call.
    Wenn der Python-Prozess Antworten kann, ist der Container "ok".
    Detailliertere Health-Logik (z.B. BFS-API-Reachability) kommt mit
    v0.2 wenn echte Live-APIs angebunden sind.

    Starlette uebergibt `request` per Konvention - aktuell unbenutzt.
    """
    del request
    return JSONResponse({"status": "ok"})


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    log.info("server.starting", port=port, transport="http")
    # Streamable-HTTP-Transport: MCP-Clients verbinden auf /mcp.
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
