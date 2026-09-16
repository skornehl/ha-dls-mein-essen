"""Constants for the DLS Mein Essen integration.

Deliberately read-only: this only reports whether Sophie is currently
registered for lunch ("Mittag") each day - it does not change anything
on the real portal. See coordinator.py/README for why.
"""
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

# How many days ahead to report on - same span as ha-blauart-kita's feed,
# kept in sync deliberately even though there's no dashboard feed here
# (just sensors/calendar) - 14 weekdays is a sensible window regardless.
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

# The one meal group this integration actually reports on.
LUNCH_GROUP_NAME = "Mittag"
