"""Sensor platform for the DLS Mein Essen integration - just today/
tomorrow's lunch registration status, read-only."""
from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DlsCoordinator, DlsLunchDay


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DlsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DlsLunchSensor(coordinator, entry, "today", 0),
            DlsLunchSensor(coordinator, entry, "tomorrow", 1),
        ]
    )


class DlsLunchSensor(CoordinatorEntity[DlsCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry, key: str, offset: int) -> None:
        super().__init__(coordinator)
        self._offset = offset
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = coordinator.device_info
        self._attr_icon = "mdi:food" if key == "today" else "mdi:food-outline"

    @property
    def _day(self) -> DlsLunchDay | None:
        return self.coordinator.data.get(date.today() + timedelta(days=self._offset))

    @property
    def native_value(self) -> str:
        day = self._day
        if day is None or not day.meal_group_offered:
            return "Kein Mittagessen"
        return "Angemeldet" if day.registered else "Abgemeldet"

    @property
    def extra_state_attributes(self) -> dict:
        day = self._day
        if day is None:
            return {}
        return {"meal_name": day.meal_name}
