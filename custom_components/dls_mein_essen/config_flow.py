"""Config flow for the DLS Mein Essen integration.

Placeholder pending the real backend API - see README.md. The DLS
portal (https://www.dls-gmbh.biz/mein-essen/) is a compiled Flutter web
app, not a plain HTML form like ha-blauart-kita's portal, so its API
host couldn't be found by inspecting the shipped JS/WASM bundle alone.
This flow accepts the same customer-number/password shape it will
eventually need, but always aborts - filled in once the real
login/fetch/select endpoints are known (see api.py, not yet written).
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_CUSTOMER_NUMBER, CONF_PASSWORD, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CUSTOMER_NUMBER): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class DlsMeinEssenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DLS Mein Essen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_abort(reason="not_implemented")

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA
        )
