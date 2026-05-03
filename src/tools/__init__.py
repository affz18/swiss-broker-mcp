"""MCP Tools - oeffentliche Funktionen die der LLM-Client aufruft.

Jedes Tool ist eine async Funktion mit:
- ausfuehrlichen Docstrings (werden vom LLM als Tool-Description gelesen!)
- Type-Hints (FastMCP generiert daraus das JSON-Schema)
- strukturiertem JSON-Output fuer das LLM
"""
