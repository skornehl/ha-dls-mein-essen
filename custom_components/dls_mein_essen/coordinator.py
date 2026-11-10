"""DataUpdateCoordinator for the DLS Mein Essen integration.

Deliberately read-only (a "crawler", not a controller): the only thing
this reports is whether Sophie is currently registered for lunch
("Mittag") on a given day - it never changes anything on the real
portal. Earlier versions of this integration also supported *changing*
the selection, but given how fiddly and slow it was to get even the
read-only login/scrape flow reliable (see the bridge add-on's README),
actually writing a real order for a real child's account wasn't worth
the risk for what turned out to only need to answer one yes/no question
per day anyway.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DlsApiError, DlsBridgeClient
from .const import (
    CONF_BRIDGE_URL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    FEED_DAYS,
    LUNCH_GROUP_NAME,
    STATUS_IN_CART,
    STATUS_NO_LUNCH,
    STATUS_NOT_REGISTERED,
    STATUS_REGISTERED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DlsLunchDay:
    """Whether Sophie is registered for lunch on this day. `has_lunch`
    is False both when she's not signed up AND when the school doesn't
    even offer a "Mittag" group that day (e.g. some Fridays, confirmed
    live) - `meal_group_offered` tells those two cases apart."""

    meal_group_offered: bool
    registered: bool
    meal_name: str | None
    # A dish sits in the portal's cart but was never checked out, so it is
    # NOT ordered (confirmed live 2026-11-03: `ordered: false`,
    # `inCartForOrder: true`, the app shows "2 Items in cart" and a small
    # cart icon on the tick). Reported separately so a forgotten checkout
    # is visible instead of looking like a plain "Abgemeldet".
    in_cart: bool = False
    cart_meal_name: str | None = None

    @property
    def status(self) -> str:
        if not self.meal_group_offered:
            return STATUS_NO_LUNCH
        if self.registered:
            return STATUS_REGISTERED
        if self.in_cart:
            return STATUS_IN_CART
        return STATUS_NOT_REGISTERED


def _monday_of(d: date_type) -> date_type:
    return d - timedelta(days=d.weekday())


def _text_from_description(description: dict) -> str:
    sections = description.get("textSections") or []
    return "".join(s.get("text", "") for s in sections).strip()


class DlsCoordinator(DataUpdateCoordinator[dict[date_type, DlsLunchDay]]):
    """Polls the dls_mein_essen_bridge add-on for however many weeks cover
    FEED_DAYS weekdays and extracts just the "Mittag" group's current
    `dish.ordered` status per day - authoritative for "is this the day's
    current selection". Since at least 2026-11-02 the portal's cart is
    active again: a dish can be ticked (`inCartForOrder`) without being
    checked out, which is tracked separately as `in_cart`."""

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

    async def _async_update_data(self) -> dict[date_type, DlsLunchDay]:
        days: dict[date_type, DlsLunchDay] = {}
        for monday in self._weeks_to_fetch():
            try:
                food_days = await self.client.async_get_food_plan(monday.isoformat())
            except DlsApiError as err:
                raise UpdateFailed(f"Speiseplan nicht abrufbar: {err}") from err

            for food_day in food_days:
                try:
                    # deliveryDate comes back as a UTC instant representing
                    # local midnight of the intended day (e.g.
                    # "2026-09-13T22:00:00+00:00" for 2026-09-14 in Berlin
                    # time) - a naive `.date()` on the raw UTC value reads
                    # off the PREVIOUS day, silently shifting every day's
                    # food data one day early (confirmed live 2026-09-17:
                    # tomorrow's dish showed up under today). Must convert
                    # to local time first.
                    raw = datetime.fromisoformat(food_day["deliveryDate"])
                    day_date = dt_util.as_local(raw).date()
                except (KeyError, ValueError):
                    continue

                lunch_group = next(
                    (
                        g
                        for g in food_day.get("mealsGroups", [])
                        if g.get("name") == LUNCH_GROUP_NAME
                    ),
                    None,
                )
                if lunch_group is None:
                    days[day_date] = DlsLunchDay(
                        meal_group_offered=False, registered=False, meal_name=None
                    )
                    continue

                registered = False
                meal_name: str | None = None
                in_cart = False
                cart_meal_name: str | None = None
                for meal in lunch_group.get("meals", []):
                    dish = meal.get("dish") or {}
                    name = _text_from_description(
                        dish.get("dishDescription", {})
                    ) or meal.get("name", "")
                    if dish.get("ordered"):
                        registered = True
                        meal_name = name
                    elif dish.get("inCartForOrder") and not in_cart:
                        in_cart = True
                        cart_meal_name = name
                days[day_date] = DlsLunchDay(
                    meal_group_offered=True,
                    registered=registered,
                    meal_name=meal_name,
                    in_cart=in_cart,
                    cart_meal_name=cart_meal_name,
                )

        return dict(sorted(days.items()))
