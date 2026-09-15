# DLS Mein Essen

Home Assistant custom integration for the [DLS "Mein Essen" school-meal
portal](https://www.dls-gmbh.biz/mein-essen/) - same idea as
[ha-blauart-kita](https://github.com/skornehl/ha-blauart-kita) (daily
meal plan + attendance sync, straight from Home Assistant), with one
key difference: this portal isn't attendance-only. Per day there are
several meal options, and **at most one** may be selected (or none) -
a single choice, not a yes/no toggle.

## Status: not functional yet

Unlike the BlauArt portal (a plain server-rendered HTML form), this one
is a compiled Flutter web app - there's no HTML to scrape, and its
backend API host couldn't be found by inspecting the shipped JS/WASM
bundle alone. The actual login/fetch/select endpoints still need to be
captured from real network traffic (browser dev tools) before `api.py`,
`coordinator.py`, and the entity platforms can be written.

What's here so far is just the repo scaffold (manifest, HACS/hassfest
CI, brand icon, a config flow that always aborts) - kept in the same
shape ha-blauart-kita ended up in, ready to fill in once the API is
known.

## Planned features (once the API is known)

- Calendar entity listing every visible day's meal option(s).
- A day-switch-style feed, but backed by a `select` entity per day
  (one of the day's meal options, or "kein Essen") instead of a plain
  on/off switch - the single-choice constraint doesn't fit a switch.
- Refresh button, same as ha-blauart-kita.
- A second tab on the existing "Verpflegung" dashboard.
