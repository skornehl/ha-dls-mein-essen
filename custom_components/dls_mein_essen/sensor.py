"""Sensor platform for the DLS Mein Essen integration.

One sensor per upcoming *weekday* (today + the next FEED_DAYS-1 school
days - weekends skipped, there's never a "Mittag" group on them anyway),
mirroring ha-blauart-kita's switch.py feed exactly (same weekday-skip
helper, same naming, same lack of `_attr_device_info` to avoid that HA
version's name-prefix quirk) so both children's dashboard tabs can use
the identical vertical-stack-per-day card layout. Read-only: state is
just "Angemeldet"/"Abgemeldet"/"Kein Mittagessen", there's nothing to
toggle here (see const.py's module docstring for why).
"""
from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FEED_DAYS, GERMAN_WEEKDAYS
from .coordinator import DlsCoordinator, DlsLunchDay


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DlsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        DlsDaySensor(coordinator, entry, offset) for offset in range(FEED_DAYS)
    ]
    # Plus one entity with a genuinely stable entity_id (unlike the feed
    # above, whose entity_id is date-slugged at creation time and drifts
    # out of sync with what it actually represents over time) - needed so
    # other automations (e.g. the morning "wer isst wo" notification) have
    # something fixed to point at instead of the moving feed.
    entities.append(DlsTodaySensor(coordinator, entry))
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


class DlsDaySensor(CoordinatorEntity[DlsCoordinator], SensorEntity):
    """`offset` (not the date) is the stable identity - entity_id stays
    put while the displayed weekday/date rolls forward daily."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:food"

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry, offset: int) -> None:
        super().__init__(coordinator)
        self._offset = offset
        self._attr_unique_id = f"{entry.entry_id}_day_{offset}"

    @property
    def _day_date(self) -> date:
        return _nth_weekday(self._offset)

    @property
    def _lunch(self) -> DlsLunchDay | None:
        return self.coordinator.data.get(self._day_date)

    @property
    def name(self) -> str:
        target = self._day_date
        return f"{GERMAN_WEEKDAYS[target.weekday()]}, {target.strftime('%d.%m.')}"

    @property
    def native_value(self) -> str:
        lunch = self._lunch
        if lunch is None or not lunch.meal_group_offered:
            return "Kein Mittagessen"
        return "Angemeldet" if lunch.registered else "Abgemeldet"

    @property
    def extra_state_attributes(self) -> dict:
        lunch = self._lunch
        if lunch is None:
            return {}
        return {"meal_name": lunch.meal_name}


class DlsTodaySensor(CoordinatorEntity[DlsCoordinator], SensorEntity):
    """`sensor.dls_mein_essen_heute` - genuinely stable entity_id (has a
    device, so this uses has_entity_name normally - no repetition problem
    since it's the only entity named this way, unlike the day feed)."""

    _attr_has_entity_name = True
    _attr_translation_key = "today"
    _attr_icon = "mdi:food"

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_today"
        self._attr_device_info = coordinator.device_info

    @property
    def _lunch(self) -> DlsLunchDay | None:
        return self.coordinator.data.get(date.today())

    @property
    def native_value(self) -> str:
        lunch = self._lunch
        if lunch is None or not lunch.meal_group_offered:
            return "Kein Mittagessen"
        return "Angemeldet" if lunch.registered else "Abgemeldet"

    @property
    def extra_state_attributes(self) -> dict:
        lunch = self._lunch
        if lunch is None:
            return {}
        return {"meal_name": lunch.meal_name}
