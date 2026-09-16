"""Sensor platform for the DLS Mein Essen integration.

Two convenience sensors (today / tomorrow), same idea as
ha-blauart-kita's - state is the current selection (or "Kein Essen") for
that day's first meal group, full option list as an attribute.
"""
from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTION_NONE
from .coordinator import DlsCoordinator, DlsMealGroup


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DlsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DlsDaySensor(coordinator, entry, "today", 0),
            DlsDaySensor(coordinator, entry, "tomorrow", 1),
        ]
    )


class DlsDaySensor(CoordinatorEntity[DlsCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry, key: str, offset: int) -> None:
        super().__init__(coordinator)
        self._offset = offset
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = coordinator.device_info
        self._attr_icon = "mdi:food" if key == "today" else "mdi:food-outline"

    @property
    def _groups(self) -> list[DlsMealGroup]:
        return self.coordinator.data.get(date.today() + timedelta(days=self._offset), [])

    @property
    def native_value(self) -> str:
        groups = self._groups
        if not groups:
            return OPTION_NONE
        group = groups[0]
        if not group.selected_dish_id:
            return OPTION_NONE
        for option in group.options:
            if option.dish_id == group.selected_dish_id:
                return option.name
        return OPTION_NONE

    @property
    def extra_state_attributes(self) -> dict:
        groups = self._groups
        return {
            "meal_groups": [
                {
                    "name": g.name,
                    "options": [o.name for o in g.options],
                    "selected": next(
                        (o.name for o in g.options if o.dish_id == g.selected_dish_id), OPTION_NONE
                    ),
                }
                for g in groups
            ]
        }
