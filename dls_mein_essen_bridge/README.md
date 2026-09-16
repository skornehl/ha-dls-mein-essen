# DLS Mein Essen Bridge

Home Assistant add-on. Not useful on its own - it's the backend the
`dls_mein_essen` custom integration talks to over `http://<addon>:8099`.

## Why this exists

The [DLS "Mein Essen"](https://www.dls-gmbh.biz/mein-essen/) portal is a
compiled Flutter web app that talks WAMP-over-WebSocket, not REST. Its
login (WAMP-CRA: PBKDF2 + HMAC-SHA256 over a server challenge) couldn't be
reproduced from a hand-written client despite having a real, known-good
challenge/signature pair to check the derivation against - something in
the exact byte-level construction still doesn't match, and guessing
further against a real account didn't feel like the right way to find out.

So instead: a real (headless) Chromium does the actual login - it's
provably correct, it's the real app - and this add-on injects its own
additional WAMP calls onto that already-authenticated WebSocket connection
(see `app/wamp_hook.js`), then exposes the results as a small local HTTP
API for the integration to consume normally.

## Configuration

- `customer_number` / `password`: same credentials as the portal itself.
- `log_level`: `debug` for full detail while getting this working the
  first time.

## First boot - this will likely need a look

The login-form automation tries Playwright's accessibility/semantic
selectors first (robust against layout changes, but Flutter web's
semantics tree isn't always reliably exposed), then falls back to a
coordinate-based click+type sequence calibrated against this specific
account's dialog layout. If it stops working, check the add-on log and
`/config/dls_login_debug.png` (written on any login failure) to see what
the page actually looked like, and adjust `_fill_login_form`'s fallback
coordinates in `app/main.py` accordingly.

One thing that cost real debugging time and is worth knowing: the app
remembers the customer number as a "saved profile" in localStorage after
the first visit to "Benutzer hinzufügen", and shows a *different* dialog
on subsequent visits that this flow isn't built for - even with
byte-verified-correct field content, login then fails. `login()` clears
cookies/local/session storage before every single attempt specifically
to avoid this, not just on first container start.

## Read-only by design

This only ever proxies one WAMP procedure (`get.caller.food.plan`) - no
write path exists here at all. An earlier version also proxied
`add.caller.order.to.cart`/`remove.caller.cart.entry` to let the
integration change the real selection, but all that was ever really
needed was a yes/no answer per day, so the write path (and the real-world
risk of a bug placing a wrong order against a real child's account) was
removed entirely.

## API

- `GET /health` → `{"ready": bool}`
- `GET /food_plan?monday=YYYY-MM-DD` → that week's food plan
