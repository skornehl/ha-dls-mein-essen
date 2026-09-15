"""Constants for the DLS Mein Essen integration."""
from __future__ import annotations

DOMAIN = "dls_mein_essen"

CONF_CUSTOMER_NUMBER = "customer_number"
CONF_PASSWORD = "password"

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
