"""Calendar platform for the DLS Mein Essen integration - one all-day
event per visible day, same idea as ha-blauart-kita's calendar.py."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    async_add_entities([DlsCalendar(coordinator, entry)])


def _selected_name(group: DlsMealGroup) -> str:
    if not group.selected_dish_id:
        return OPTION_NONE
    for option in group.options:
        if option.dish_id == group.selected_dish_id:
            return option.name
    return OPTION_NONE


def _event_for_day(day: date, groups: list[DlsMealGroup]) -> CalendarEvent | None:
    if not groups:
        return None
    lines = []
    for group in groups:
        status = _selected_name(group)
        lines.append(f"{group.name}: {status}")
        for option in group.options:
            marker = "✅" if option.dish_id == group.selected_dish_id else "▫️"
            lines.append(f"  {marker} {option.name}")
    summary = " / ".join(f"{g.name}: {_selected_name(g)}" for g in groups)
    return CalendarEvent(start=day, end=day + timedelta(days=1), summary=summary, description="\n".join(lines))


class DlsCalendar(CoordinatorEntity[DlsCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "plan"
    _attr_icon = "mdi:food"

    def __init__(self, coordinator: DlsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = coordinator.device_info

    @property
    def event(self) -> CalendarEvent | None:
        today = date.today()
        for day, groups in self.coordinator.data.items():
            if day >= today:
                event = _event_for_day(day, groups)
                if event is not None:
                    return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events = []
        for day, groups in self.coordinator.data.items():
            if start_date.date() <= day < end_date.date():
                event = _event_for_day(day, groups)
                if event is not None:
                    events.append(event)
        return events
