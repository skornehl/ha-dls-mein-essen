# DLS Mein Essen

Home Assistant custom integration for the [DLS "Mein Essen" school-meal
portal](https://www.dls-gmbh.biz/mein-essen/). Deliberately a pure,
read-only crawler, not a controller: it answers exactly one question per
day - **is Sophie currently registered for lunch ("Mittag")?** - and
never changes anything on the real portal.

(An earlier version also supported *changing* the selection, mirroring
[ha-blauart-kita](https://github.com/skornehl/ha-blauart-kita)'s
attendance-sync feature. Given how fiddly it was to get even the
read-only login/scrape flow reliable against this portal's compiled
Flutter web app, actually writing a real order for a real child's account
wasn't worth the risk for what only ever needed to answer a yes/no
question - so the write path was removed entirely, see the bridge
add-on's changelog.)

## Two parts

- **DLS Mein Essen Bridge** (Home Assistant add-on, published from
  [skornehl/ha-addons](https://github.com/skornehl/ha-addons)) - the portal is a
  compiled Flutter web app that talks WAMP-over-WebSocket, not REST, and
  its login (WAMP-CRA: PBKDF2 + HMAC-SHA256 over a server challenge)
  couldn't be reproduced from a hand-written client despite having a
  real, known-good challenge/signature pair to check the derivation
  against. So a real headless Chromium does the actual login instead -
  it's provably correct, it's the real app - and the add-on rides along
  on that already-authenticated WebSocket to read the food plan, exposed
  as a small local HTTP API.
- **`dls_mein_essen`** (this HACS integration) - talks to the bridge
  add-on's HTTP API, not to the portal directly.

Install both: the add-on (add `https://github.com/skornehl/ha-addons` as
an add-on repository) and the integration (add this repo as a HACS custom
repository).

## Features

- **Calendar entity** - one event per visible weekday: registered
  (✅, with the meal name) or not (❌). Days with no "Mittag" group at
  all (some Fridays, confirmed live) don't get an event.
- **Today / Tomorrow sensors** - "Angemeldet" / "Abgemeldet" / "Kein
  Mittagessen".
- **Refresh button** - forces an immediate re-check instead of waiting
  out the 6h poll interval.

## Installation

1. Add-on: Settings → Add-ons → Add-on Store → ⋮ → Repositories → add
   `https://github.com/skornehl/ha-addons`, install "DLS Mein Essen
   Bridge", configure your DLS customer number/password, start it. Check
   its log the first time - see the add-on's README if the login
   automation needs tuning against the real page layout.
2. Integration: via [HACS](https://hacs.xyz/), add this repository as a
   custom repository (category: Integration), install "DLS Mein Essen",
   then add it in Settings → Devices & Services (the bridge add-on's URL
   defaults to its Supervisor-assigned hostname
   `http://6dc2c37d-dls-mein-essen-bridge:8099`; **Reconfigure** on the
   entry changes it later).

## Moving from the old add-on

Up to bridge 0.2.3 the add-on was published from this repository. It now
lives in [skornehl/ha-addons](https://github.com/skornehl/ha-addons); the
copy in `dls_mein_essen_bridge/` here gets no further updates. To switch:
add the new add-on repository, install the bridge from there and enter the
same credentials, stop the old bridge, then open the integration and choose
**Reconfigure** - the default URL is the new bridge
(`http://6dc2c37d-dls-mein-essen-bridge:8099`). Entities and history stay.
Finally uninstall the old add-on.
