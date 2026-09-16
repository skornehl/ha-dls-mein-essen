# DLS Mein Essen

Home Assistant custom integration for the [DLS "Mein Essen" school-meal
portal](https://www.dls-gmbh.biz/mein-essen/) - same idea as
[ha-blauart-kita](https://github.com/skornehl/ha-blauart-kita) (daily
meal plan + attendance sync, straight from Home Assistant), with one key
difference: this portal isn't attendance-only. Per day there are several
meal options, and **at most one** may be selected (or none) - a single
choice, not a yes/no toggle, so this integration exposes `select`
entities instead of `switch` entities.

## Two parts

- **`dls_mein_essen_bridge`** (Home Assistant add-on) - the portal is a
  compiled Flutter web app that talks WAMP-over-WebSocket, not REST, and
  its login (WAMP-CRA: PBKDF2 + HMAC-SHA256 over a server challenge)
  couldn't be reproduced from a hand-written client despite having a
  real, known-good challenge/signature pair to check the derivation
  against. So a real headless Chromium does the actual login instead -
  it's provably correct, it's the real app - and the add-on rides along
  on that already-authenticated WebSocket to make its own additional
  calls, exposed as a small local HTTP API.
- **`dls_mein_essen`** (this HACS integration) - talks to the bridge
  add-on's HTTP API, not to the portal directly.

Install both: the add-on (add this repo as an add-on repository) and the
integration (add this repo as a HACS custom repository).

## Features

- **Calendar entity** listing every visible day, each meal group and its
  options plus the current selection.
- **Today / Tomorrow sensors**.
- **A 14-weekday select feed** (today + the next 13 school days, weekends
  skipped), one `select` entity per day per meal group, options are
  whatever the portal offers that day plus "Kein Essen" - selecting
  syncs to the real portal optimistically (instant UI feedback, real sync
  happens in the background) with a revert-on-failure safety net, same
  as ha-blauart-kita's switches.
- **Refresh button**.

## Installation

1. Add-on: Settings → Add-ons → Add-on Store → ⋮ → Repositories → add
   `https://github.com/skornehl/ha-dls-mein-essen`, install "DLS Mein
   Essen Bridge", configure your DLS customer number/password, start it.
   Check its log the first time - see `dls_mein_essen_bridge/README.md`
   if the login automation needs tuning against the real page layout.
2. Integration: via [HACS](https://hacs.xyz/), add this repository as a
   custom repository (category: Integration), install "DLS Mein Essen",
   then add it in Settings → Devices & Services (the bridge add-on's URL
   defaults to `http://dls_mein_essen_bridge:8099`, Home Assistant's
   internal network should resolve that without any extra config).
