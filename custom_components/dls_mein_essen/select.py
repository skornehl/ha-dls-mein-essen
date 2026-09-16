"""Select platform for the DLS Mein Essen integration.

The core difference from ha-blauart-kita: this portal isn't a plain
yes/no attendance toggle - each day (per meal group, e.g. "Frühstück")
offers several dishes, of which *at most one* may be chosen. A switch
can't represent "exactly one of N, or none" - a select entity can, with
"Kein Essen" as an always-available extra option alongside whatever the
portal is actually offering that day.

One select per (weekday offset, meal-group slot) - weekends skipped
entirely (see _nth_weekday), same reasoning as ha-blauart-kita's feed.
Slots beyond how many groups a given day actually has just stay
unavailable rather than being created/destroyed dynamically.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import DlsApiError
from .const import DOMAIN, FEED_DAYS, GERMAN_WEEKDAYS, MAX_MEAL_GROUPS_PER_DAY, OPTION_NONE
from .coordinator import DlsCoordinator, DlsMealGroup, DlsMealOption

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DlsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DlsMealSelect(coordinator, entry, offset, slot)
        for offset in range(FEED_DAYS)
        for slot in range(MAX_MEAL_GROUPS_PER_DAY)
    ]
    async_add_entities(entities)


def _nth_weekday(offset: int) -> date:
    """The `offset`-th weekday (Mon-Fri) counting today as 0 - identical
    to ha-blauart-kita's switch.py, kept in sync deliberately."""
    d = date.today()
    remaining = offset
    while True:
        if d.weekday() < 5:
            if remaining == 0:
                return d
            remaining -= 1
        d += timedelta(days=1)


class DlsMealSelect(CoordinatorEntity[DlsCoordinator], SelectEntity):
    """`offset`/`slot` (not the date/group name) are the stable identity -
    entity_id stays put while the displayed date and available options
    roll forward/change daily. No `_attr_device_info` here, same lesson
    learned in ha-blauart-kita's switch.py: assigning a device made this
    HA version prefix every name with the device name regardless of
    has_entity_name."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:food"

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry, offset: int, slot: int) -> None:
        super().__init__(coordinator)
        self._offset = offset
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_day_{offset}_group_{slot}"
        self._optimistic: str | None = None
        self._sync_lock = asyncio.Lock()

    @property
    def _day_date(self) -> date:
        return _nth_weekday(self._offset)

    @property
    def _group(self) -> DlsMealGroup | None:
        groups = self.coordinator.data.get(self._day_date, [])
        if self._slot < len(groups):
            return groups[self._slot]
        return None

    @property
    def name(self) -> str:
        target = self._day_date
        label = f"{GERMAN_WEEKDAYS[target.weekday()]}, {target.strftime('%d.%m.')}"
        group = self._group
        if group is not None and group.name:
            label += f" - {group.name}"
        return label

    @property
    def available(self) -> bool:
        group = self._group
        return super().available and group is not None and bool(group.options)

    @property
    def options(self) -> list[str]:
        group = self._group
        names = [OPTION_NONE]
        if group is not None:
            names.extend(o.name for o in group.options if o.name)
        return names

    @property
    def current_option(self) -> str | None:
        if self._optimistic is not None:
            return self._optimistic
        group = self._group
        if group is None or not group.selected_dish_id:
            return OPTION_NONE
        for option in group.options:
            if option.dish_id == group.selected_dish_id:
                return option.name
        return OPTION_NONE

    @property
    def extra_state_attributes(self) -> dict:
        group = self._group
        if group is None:
            return {}
        return {"meal_group": group.name, "options": [o.name for o in group.options]}

    async def async_select_option(self, option: str) -> None:
        group = self._group
        if group is None:
            raise HomeAssistantError("Für diesen Tag/diese Essensgruppe liegen keine Daten vor")

        chosen: DlsMealOption | None = None
        if option != OPTION_NONE:
            chosen = next((o for o in group.options if o.name == option), None)
            if chosen is None:
                raise HomeAssistantError(f"Unbekannte Option: {option}")

        # Optimistic: flip the shown selection instantly, sync to the
        # portal (via the bridge add-on's already-authenticated browser
        # session) in the background - same reasoning as ha-blauart-kita's
        # switch.py, a tap should feel instant.
        self._optimistic = option
        self.async_write_ha_state()
        self.hass.async_create_task(
            self._async_sync_to_portal(group, chosen),
            name=f"dls_mein_essen select {self._day_date} slot {self._slot}",
        )

    async def _async_sync_to_portal(self, group: DlsMealGroup, chosen: DlsMealOption | None) -> None:
        async with self._sync_lock:
            try:
                await self.coordinator.async_select_meal(self._day_date, group, chosen)
            except DlsApiError as err:
                _LOGGER.error(
                    "DLS: Essensauswahl für %s (%s) konnte nicht gespeichert werden: %s",
                    self._day_date,
                    group.name,
                    err,
                )
                persistent_notification.async_create(
                    self.hass,
                    f"{self.name}: Änderung konnte nicht gespeichert werden ({err}). "
                    "Bitte im Portal prüfen.",
                    title="DLS Mein Essen",
                    notification_id=f"dls_mein_essen_sync_failed_{self.unique_id}",
                )
                await self.coordinator.async_request_refresh()
            finally:
                self._optimistic = None
                self.async_write_ha_state()
