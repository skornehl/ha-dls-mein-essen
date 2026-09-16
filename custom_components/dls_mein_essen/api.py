"""Client for the dls_mein_essen_bridge add-on's local HTTP API.

The DLS "Mein Essen" portal itself speaks WAMP-over-WebSocket, not REST -
see the dls_mein_essen_bridge add-on's README for why this integration
doesn't talk to the portal directly (the WAMP-CRA login signature
couldn't be reproduced outside a real browser). The bridge add-on runs
that real browser and exposes a small REST API instead; this file is a
thin wrapper around exactly that API, not around the portal itself.
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

    async def async_select_meal(
        self,
        delivery_date: str,
        meal_group_id: str,
        meal_id: str,
        dish_id: str | None = None,
        planning_slot_id: str | None = None,
    ) -> None:
        payload = {
            "delivery_date": delivery_date,
            "meal_group_id": meal_group_id,
            "meal_id": meal_id,
        }
        if dish_id:
            payload["dish_id"] = dish_id
        if planning_slot_id:
            payload["planning_slot_id"] = planning_slot_id
        async with self._session.post(
            f"{self._base_url}/select_meal", json=payload, timeout=TIMEOUT
        ) as resp:
            if resp.status >= 400:
                raise DlsApiError(f"select_meal request failed: HTTP {resp.status}")

    async def async_clear_meal(self, dish_id: str) -> None:
        async with self._session.post(
            f"{self._base_url}/clear_meal", json={"dish_id": dish_id}, timeout=TIMEOUT
        ) as resp:
            if resp.status >= 400:
                raise DlsApiError(f"clear_meal request failed: HTTP {resp.status}")
