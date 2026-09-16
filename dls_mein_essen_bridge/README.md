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
coordinate-based click+type sequence with hardcoded guesses. If both fail,
check the add-on log and `/config/dls_login_debug.png` (written on any
login failure) to see what the page actually looked like, and adjust
`_fill_login_form`'s fallback coordinates in `app/main.py` accordingly.

## API

- `GET /health` → `{"ready": bool}`
- `GET /food_plan?monday=YYYY-MM-DD` → that week's food plan
- `POST /select_meal` `{delivery_date, meal_group_id, meal_id, dish_id?}`
- `POST /clear_meal` `{dish_id}`
