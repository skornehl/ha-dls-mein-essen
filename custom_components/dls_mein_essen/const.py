"""Constants for the DLS Mein Essen integration."""
from __future__ import annotations

DOMAIN = "dls_mein_essen"

CONF_BRIDGE_URL = "bridge_url"
DEFAULT_BRIDGE_URL = "http://dls_mein_essen_bridge:8099"

DEFAULT_SCAN_INTERVAL_SECONDS = 6 * 60 * 60  # 6h, same reasoning as
# ha-blauart-kita - the menu doesn't change often enough to poll harder.

# Same feed length as ha-blauart-kita (see FEED_DAYS there) - kept in
# sync deliberately so both children's dashboards behave the same way.
FEED_DAYS = 14

GERMAN_WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

# "Kein Essen" is always a valid choice alongside whatever the portal
# actually offers that day - this is what a select entity's "off" state
# maps to (see select.py).
OPTION_NONE = "Kein Essen"

# Max meal groups (Frühstück/Mittag/...) handled per day - the one real
# account we've seen data from only ever showed one ("Frühstück"), but
# nothing guarantees that's universal, so a few spare slots are created
# per day and just stay unavailable if a day doesn't have that many.
MAX_MEAL_GROUPS_PER_DAY = 3

