"""Constants for the DLS Mein Essen integration."""
from __future__ import annotations

DOMAIN = "dls_mein_essen"

CONF_BRIDGE_URL = "bridge_url"
DEFAULT_BRIDGE_URL = "http://630e259d-dls-mein-essen-bridge:8099"
# The hash prefix is specific to how the bridge add-on's repository was
# installed on this instance (Supervisor generates it from the repo URL
# for local/custom-repository add-ons, unlike official add-ons' plain
# slugs) - if reinstalled on a different instance, check Settings ->
# Add-ons -> DLS Mein Essen Bridge -> Info for the real hostname, or just
# use its IP address instead.

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

# Max meal groups (Frühstück/Milch/Getränke/Mittag/...) handled per day -
# confirmed live against the real account: 4 on a typical day. 5 gives one
# spare slot; days with fewer groups just leave the extra slots
# unavailable rather than entities being dynamically created/destroyed.
MAX_MEAL_GROUPS_PER_DAY = 5

