"""In-Memory TTL Cache.

Einfacher async-tauglicher Decorator-Cache fuer HTTP-Responses externer
APIs. Default TTL: 3600s (1h) - BFS-Daten aendern sich quartalsweise.

Bewusst NICHT Redis o.ae.: wir laufen pro Cloud Run Instanz, kalter Start
ist OK, und horizontale Skalierung ist fuer einen Daten-Bridge-MCP nicht
kritisch. Sollte sich das aendern, kann der Decorator durch eine
Redis-basierte Variante ersetzt werden, ohne dass Tool-Code angefasst
werden muss.

Beispiel:
    @cached(ttl_seconds=3600)
    async def fetch_bfs_index(canton: str) -> dict[str, float]:
        ...
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


def cached(
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator: cached eine async Funktion in-memory nach (args, kwargs).

    Threadsafe innerhalb eines asyncio Event-Loops.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        store: dict[tuple[Any, ...], tuple[float, R]] = {}
        lock = asyncio.Lock()

        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key: tuple[Any, ...] = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            async with lock:
                cached_entry = store.get(key)
                if cached_entry is not None:
                    expires_at, value = cached_entry
                    if expires_at > now:
                        return value
            # Achtung: factory-Call AUSSERHALB des Locks, sonst blockieren
            # parallele Aufrufe auf unterschiedliche Keys.
            value = await fn(*args, **kwargs)
            async with lock:
                store[key] = (time.monotonic() + ttl_seconds, value)
            return value

        return wrapper

    return decorator
