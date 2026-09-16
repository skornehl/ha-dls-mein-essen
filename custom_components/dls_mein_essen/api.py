"""Client for the dls_mein_essen_bridge add-on's local HTTP API.

The DLS "Mein Essen" portal itself speaks WAMP-over-WebSocket, not REST -
see the dls_mein_essen_bridge add-on's README for why this integration
doesn't talk to the portal directly (the WAMP-CRA login signature
couldn't be reproduced outside a real browser). The bridge add-on runs
that real browser and exposes a small REST API instead; this file is a
thin wrapper around exactly that API, not around the portal itself.

Read-only on purpose: this only asks for the food plan, never for the
bridge's write endpoints (which still exist add-on-side but aren't
called from here) - see const.py's module docstring for why.
"""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=20)


class DlsApiError(Exception):
    """Raised on any bridge-level failure (unreachable, not logged in, ...)."""


class DlsBridgeClient:
    """Wrapper around the dls_mein_essen_bridge add-on's HTTP API."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def async_check_health(self) -> bool:
        try:
            async with self._session.get(f"{self._base_url}/health", timeout=TIMEOUT) as resp:
                if resp.status >= 400:
                    return False
                data = await resp.json()
                return bool(data.get("ready"))
        except Exception as err:  # noqa: BLE001
            raise DlsApiError(f"Bridge unreachable: {err}") from err

    async def async_get_food_plan(self, monday: str) -> list[dict[str, Any]]:
        """`monday`: ISO date (YYYY-MM-DD) of that week's Monday. Returns
        the raw `foodDays` list for that week."""
        async with self._session.get(
            f"{self._base_url}/food_plan", params={"monday": monday}, timeout=TIMEOUT
        ) as resp:
            if resp.status >= 400:
                raise DlsApiError(f"food_plan request failed: HTTP {resp.status}")
            data = await resp.json()
        if not data:
            return []
        return data[0].get("foodDays", [])
