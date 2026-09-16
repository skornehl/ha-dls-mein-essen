"""DataUpdateCoordinator for the DLS Mein Essen integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type, datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DlsApiError, DlsBridgeClient
from .const import CONF_BRIDGE_URL, DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN, FEED_DAYS

_LOGGER = logging.getLogger(__name__)


@dataclass
class DlsMealOption:
    """One choice within a meal group (e.g. one of several lunch options)."""

    meal_id: str
    dish_id: str | None
    name: str


@dataclass
class DlsMealGroup:
    """A single decision point for a day - "Frühstück"/"Mittag"/etc. Exactly
    one of `options` (or none) may be selected, never more than one - see
    select.py, this is why it's a select entity and not a switch."""

    group_id: str
    name: str
    order_number: int
    options: list[DlsMealOption] = field(default_factory=list)
    selected_dish_id: str | None = None


def _monday_of(d: date_type) -> date_type:
    return d - timedelta(days=d.weekday())


def _text_from_description(description: dict) -> str:
    sections = description.get("textSections") or []
    return "".join(s.get("text", "") for s in sections).strip()


class DlsCoordinator(DataUpdateCoordinator[dict[date_type, list[DlsMealGroup]]]):
    """Polls the dls_mein_essen_bridge add-on for however many weeks cover
    FEED_DAYS weekdays, plus the current cart, and merges them into a
    date-keyed dict of meal groups with their current selection resolved."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.client = DlsBridgeClient(async_get_clientsession(hass), entry.data[CONF_BRIDGE_URL])
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="DLS Mein Essen",
            manufacturer="DLS Dienstleistungs- und Service GmbH",
            model="Mein Essen Kundenportal",
            configuration_url="https://www.dls-gmbh.biz/mein-essen/",
        )

    def _weeks_to_fetch(self) -> list[date_type]:
        today = date_type.today()
        last_day = today + timedelta(days=FEED_DAYS + 7)  # generous pad for weekends skipped elsewhere
        mondays = set()
        d = _monday_of(today)
        while d <= last_day:
            mondays.add(d)
            d += timedelta(days=7)
        return sorted(mondays)

    async def _async_update_data(self) -> dict[date_type, list[DlsMealGroup]]:
        try:
            cart_entries = await self.client.async_get_cart()
        except DlsApiError as err:
            raise UpdateFailed(f"Bridge nicht erreichbar: {err}") from err

        # dish_id -> True for anything currently in the cart, keyed also by
        # date to avoid cross-day collisions if a dish id is ever reused.
        cart_dish_ids: set[str] = set()
        for entry in cart_entries:
            dish_id = entry.get("dishId") or entry.get("dish", {}).get("id")
            if dish_id:
                cart_dish_ids.add(dish_id)

        days: dict[date_type, list[DlsMealGroup]] = {}
        for monday in self._weeks_to_fetch():
            try:
                food_days = await self.client.async_get_food_plan(monday.isoformat())
            except DlsApiError as err:
                raise UpdateFailed(f"Speiseplan nicht abrufbar: {err}") from err

            for food_day in food_days:
                try:
                    day_date = datetime.fromisoformat(food_day["deliveryDate"]).date()
                except (KeyError, ValueError):
                    continue
                groups: list[DlsMealGroup] = []
                for raw_group in food_day.get("mealsGroups", []):
                    options: list[DlsMealOption] = []
                    selected_dish_id: str | None = None
                    for meal in raw_group.get("meals", []):
                        dish = meal.get("dish") or {}
                        dish_id = dish.get("id")
                        name = _text_from_description(dish.get("dishDescription", {})) or meal.get(
                            "name", ""
                        )
                        options.append(
                            DlsMealOption(meal_id=meal.get("id", ""), dish_id=dish_id, name=name)
                        )
                        if dish_id and dish_id in cart_dish_ids:
                            selected_dish_id = dish_id
                    groups.append(
                        DlsMealGroup(
                            group_id=raw_group.get("mealGroupId", ""),
                            name=raw_group.get("name", ""),
                            order_number=raw_group.get("orderNumber", 0),
                            options=options,
                            selected_dish_id=selected_dish_id,
                        )
                    )
                groups.sort(key=lambda g: g.order_number)
                days[day_date] = groups

        return dict(sorted(days.items()))

    async def async_select_meal(
        self, target_date: date_type, group: DlsMealGroup, option: DlsMealOption | None
    ) -> None:
        """`option=None` means "kein Essen" - clears whatever's currently
        selected for this group instead of adding a new one."""
        if option is None:
            if group.selected_dish_id:
                await self.client.async_clear_meal(group.selected_dish_id)
        else:
            # The portal only allows one selection per group - clear
            # anything already picked first so we don't end up with two
            # entries for the same day/group.
            if group.selected_dish_id and group.selected_dish_id != option.dish_id:
                await self.client.async_clear_meal(group.selected_dish_id)
            await self.client.async_select_meal(
                delivery_date=target_date.isoformat(),
                meal_group_id=group.group_id,
                meal_id=option.meal_id,
                dish_id=option.dish_id,
            )
        await self.async_request_refresh()
