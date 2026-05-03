"""FastMCP Server Entry Point.

Registriert alle Tools und startet den Server im SSE-Transport (HTTP),
sodass Cloud Run ihn auf $PORT bedienen kann. Claude Desktop und andere
MCP-Clients verbinden sich per `https://<host>/sse`.

Logging: structlog im JSON-Format - Cloud Run Logging parst das
automatisch in strukturierte Felder.
"""

from __future__ import annotations

import logging
import os
import sys

import structlog
from dotenv import load_dotenv
from fastmcp import FastMCP

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
# TODO Step 3: mcp.tool()(get_acquisition_email_context)
# TODO Step 4: mcp.tool()(get_neighborhood_profile)


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    log.info("server.starting", port=port, transport="sse")
    # SSE-Transport: HTTP-Endpoint /sse fuer MCP-Clients (Claude Desktop u.a.).
    mcp.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
