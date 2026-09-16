"""Button platform for the DLS Mein Essen integration - a manual refresh
button, same reasoning as ha-blauart-kita's (homeassistant.update_entity
is a no-op for coordinator-backed entities on this HA version)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DlsCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DlsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DlsRefreshButton(coordinator, entry)])


class DlsRefreshButton(CoordinatorEntity[DlsCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
