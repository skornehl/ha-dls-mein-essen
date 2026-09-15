"""The DLS Mein Essen integration.

Not functional yet - the config flow always aborts (see config_flow.py)
until the real backend API is known, so this never actually runs
against a config entry in practice. Kept minimal and valid so hassfest/
HACS validation passes from day one, same as ha-blauart-kita's pipeline
was set up before its own api.py existed.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
