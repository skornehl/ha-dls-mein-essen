"""Config flow for the DLS Mein Essen integration.

Unlike ha-blauart-kita, there's no customer number/password to enter here
- those live in the dls_mein_essen_bridge add-on's own config (it's the
one that logs in). All this flow needs is the bridge's URL, and it
actively checks reachability before accepting it.
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DlsApiError, DlsBridgeClient
from .const import CONF_BRIDGE_URL, DEFAULT_BRIDGE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_BRIDGE_URL, default=DEFAULT_BRIDGE_URL): str})


class DlsMeinEssenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DLS Mein Essen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_BRIDGE_URL])
            self._abort_if_unique_id_configured()

            client = DlsBridgeClient(async_get_clientsession(self.hass), user_input[CONF_BRIDGE_URL])
            try:
                await client.async_check_health()
            except DlsApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error checking bridge health")
                errors["base"] = "unknown"
            else:
                # Not requiring ready=True here - the bridge might still be
                # logging in on first start, and that shouldn't block setup;
                # the coordinator will just retry until it succeeds.
                return self.async_create_entry(title="DLS Mein Essen", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
