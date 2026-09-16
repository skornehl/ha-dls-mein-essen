"""DLS Mein Essen Bridge - runs a real headless browser logged into the
DLS "Mein Essen" portal and exposes its authenticated WAMP session as a
small local HTTP API.

Why this exists: the portal's WAMP-CRA login (PBKDF2 + HMAC-SHA256 over a
server-issued challenge) couldn't be reproduced from a hand-written Python
client despite having a real, known-good challenge/signature pair to check
against - something in the exact byte-level derivation still doesn't
match. Rather than keep guessing against a real account, a real browser
does the login (it's provably correct - it's the actual app), and this
add-on just rides along on that already-authenticated WebSocket to make
its own additional WAMP calls (see wamp_hook.js) - no server-side attempt
counter to worry about, no more guessing.

This is deliberately NOT a general-purpose scraper: it only ever proxies
the handful of WAMP procedures the dls_mein_essen integration needs
(get.caller.food.plan, add.caller.order.to.cart, remove.caller.cart.entry).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pydantic import BaseModel
import uvicorn

LOGIN_URL = "https://www.dls-gmbh.biz/mein-essen/#/login"
WAMP_HOOK_JS = (Path(__file__).parent / "wamp_hook.js").read_text()
DEBUG_SCREENSHOT_PATH = "/config/dls_login_debug.png"
OPTIONS_PATH = "/data/options.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_LOGGER = logging.getLogger("dls_bridge")


def load_options() -> dict[str, str]:
    with open(OPTIONS_PATH) as f:
        return json.load(f)


class Bridge:
    """Owns the single persistent browser/page and the login lifecycle."""

    def __init__(self, customer_number: str, password: str) -> None:
        self.customer_number = customer_number
        self.password = password
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None
        self._lock = asyncio.Lock()
        self.ready = False

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="de-DE",
            extra_http_headers={"Accept-Language": "de-DE,de;q=0.9"},
        )
        self.page = await self._context.new_page()
        await self.page.add_init_script(WAMP_HOOK_JS)
        asyncio.create_task(self._watchdog())

    async def _watchdog(self) -> None:
        """Keeps us logged in - checks the WS session periodically and
        re-logs-in if it ever drops (network hiccup, server-side session
        timeout, portal restart, ...)."""
        while True:
            try:
                if self.page is None:
                    await asyncio.sleep(10)
                    continue
                ready = await self.page.evaluate("() => window.__wampReady === true")
                if not ready:
                    _LOGGER.warning("WAMP session not ready, (re)logging in")
                    await self.login()
                self.ready = ready or self.ready
            except Exception:
                _LOGGER.exception("Watchdog iteration failed")
            await asyncio.sleep(30)

    async def login(self) -> bool:
        async with self._lock:
            page = self.page
            assert page is not None
            _LOGGER.info("Navigating to login page")
            await page.goto(LOGIN_URL, wait_until="networkidle")
            # Flutter engine boot (CanvasKit/Skwasm download+init) takes a
            # few seconds even on a fast connection - no reliable DOM event
            # to wait on, so just give it a generous head start.
            await page.wait_for_timeout(4000)

            filled = await self._fill_login_form(page)
            if not filled:
                await self._save_debug_screenshot(page, "form-fill-failed")
                return False

            for _ in range(20):
                ready = await page.evaluate("() => window.__wampReady === true")
                if ready:
                    _LOGGER.info("Login successful (WAMP WELCOME received)")
                    self.ready = True
                    return True
                error = await page.evaluate("() => window.__wampLastError")
                if error:
                    _LOGGER.error("WAMP login aborted: %s", error)
                    await self._save_debug_screenshot(page, "wamp-abort")
                    return False
                await page.wait_for_timeout(1000)

            _LOGGER.error("Login timed out waiting for WAMP WELCOME")
            await self._save_debug_screenshot(page, "login-timeout")
            return False

    async def _fill_login_form(self, page: Page) -> bool:
        """Navigating straight to #/login lands on a "Profiles" screen
        with a sidebar, not a login form directly - there's a "Login" nav
        item (or an "Add user" tile, description: "Use your customer
        number and password") that actually gets to the two-field form.
        Bilingual matching throughout since the app renders in whatever
        the browser context's locale/Accept-Language implies (we set
        de-DE in start(), but matching both is cheap insurance against
        the app not honoring it for some reason - it clearly didn't
        before that was added, see the first debug screenshot).

        Two strategies, in order:

        1. Accessibility/semantic selectors - Flutter web exposes a
           semantics tree for screen readers that Playwright's role-based
           selectors can often find, and layout changes don't break it.
        2. Coordinate-based click+type fallback - Flutter's CanvasKit
           renderer draws to a <canvas>, so there usually isn't a normal
           DOM <input> to target; this WILL need tuning against the real
           page (see README's "first boot" note) since exact coordinates
           depend on the actual rendered layout.
        """
        # Sidebar "Login" nav item - just gets to a "Profiles" screen, not
        # a form (see below), but does need clicking first.
        await self._click_text_or_coords(page, r"^(Login|Anmelden)$", (100, 114), "Login nav item")
        await self._debug_screenshot(page, "step1_after_login_click")

        # A "Wichtige Service-Information" maintenance-notice modal can
        # cover the whole screen (confirmed via debug screenshot - the
        # 'Benutzer hinzufügen' click below was silently swallowed by it).
        # Harmless to attempt even when there's nothing to dismiss - the
        # coordinate fallback just taps empty background in that case.
        await self._click_text_or_coords(page, r"^OK$", (848, 583), "maintenance notice dismiss")
        await self._debug_screenshot(page, "step1b_after_dismiss")

        # The "Profiles" screen's "Benutzer hinzufügen"/"Add user" tile
        # ("Login mit Kundennummer und Passwort") is what actually gets to
        # the two-field form - confirmed via a debug screenshot, this
        # portal's login is a two-step navigation, not a direct form.
        await self._click_text_or_coords(
            page,
            r"Benutzer hinzuf.gen|Add user",
            (740, 756),
            "'Benutzer hinzufügen' tile",
        )
        await self._debug_screenshot(page, "step2_after_adduser_click")

        # Always capture what the form actually looks like right before
        # attempting to fill it in - purely for calibrating the
        # coordinate fallback below across iterations, regardless of
        # whether this attempt ultimately succeeds.
        await self._debug_screenshot(page, "form_debug")

        try:
            number_field = page.get_by_role(
                "textbox", name=re.compile("Kundennummer|Customer number", re.I)
            )
            await number_field.click(timeout=5000)
            await page.keyboard.type(self.customer_number, delay=30)

            password_field = page.get_by_role("textbox", name=re.compile("Passwort|Password", re.I))
            await password_field.click(timeout=5000)
            await page.keyboard.type(self.password, delay=30)

            login_button = page.get_by_role(
                "button", name=re.compile("Anmelden|Einloggen|Login|Log ?in|Sign ?in", re.I)
            )
            await login_button.click(timeout=5000)
            _LOGGER.info("Filled login form via semantic selectors")
            return True
        except Exception as err:
            _LOGGER.warning("Semantic selectors failed (%s), trying coordinate fallback", err)

        try:
            # Best-effort default layout guess for a 1280x900 viewport -
            # a centered login card with two stacked fields. Almost
            # certainly needs adjusting once we see the real page (see
            # README) - that's expected, not a sign something's broken.
            await page.mouse.click(640, 380)
            await page.keyboard.type(self.customer_number, delay=30)
            await page.keyboard.press("Tab")
            await page.keyboard.type(self.password, delay=30)
            await page.keyboard.press("Enter")
            _LOGGER.info("Filled login form via coordinate fallback")
            return True
        except Exception:
            _LOGGER.exception("Coordinate fallback also failed")
            return False

    async def _click_text_or_coords(
        self, page: Page, pattern: str, coords: tuple[int, int], description: str
    ) -> None:
        """Try to click something by its (semantic) text first, fall back
        to a raw coordinate click - Flutter's CanvasKit renderer draws to
        a <canvas>, so there's usually no real text node for
        get_by_text/get_by_role to find, but it's cheap insurance in case
        a given screen genuinely does expose one."""
        try:
            await page.get_by_text(re.compile(pattern, re.I)).first.click(timeout=5000)
            _LOGGER.info("Clicked %s via text selector", description)
        except Exception as err:
            _LOGGER.info("Text selector for %s failed (%s), using coordinates", description, err)
            try:
                await page.mouse.click(*coords)
                _LOGGER.info("Clicked %s via coordinates %s", description, coords)
            except Exception:
                _LOGGER.exception("Coordinate click for %s also failed", description)
        await page.wait_for_timeout(2500)

    async def _debug_screenshot(self, page: Page, tag: str) -> None:
        try:
            os.makedirs("/config", exist_ok=True)
            await page.screenshot(path=f"/config/dls_{tag}.png")
        except Exception:
            _LOGGER.exception("Could not save debug screenshot (%s)", tag)

    async def _save_debug_screenshot(self, page: Page, reason: str) -> None:
        try:
            os.makedirs("/config", exist_ok=True)
            await page.screenshot(path=DEBUG_SCREENSHOT_PATH)
            _LOGGER.error(
                "Saved debug screenshot to %s (reason: %s) - check it via the "
                "add-on's config folder (Samba/File editor) to see what the "
                "login page actually looked like",
                DEBUG_SCREENSHOT_PATH,
                reason,
            )
        except Exception:
            _LOGGER.exception("Could not save debug screenshot")

    async def call(self, procedure: str, args: list | None = None, kwargs: dict | None = None) -> Any:
        if not self.ready or self.page is None:
            raise HTTPException(status_code=503, detail="Not logged in yet")
        try:
            result = await self.page.evaluate(
                "([proc, args, kwargs]) => window.__wampCall(proc, args, kwargs)",
                [procedure, args or [], kwargs or {}],
            )
        except Exception as err:
            raise HTTPException(status_code=502, detail=f"WAMP call failed: {err}") from err
        # result is the raw WAMP RESULT message: [50, reqId, details, args, kwargs]
        if len(result) >= 4 and result[3]:
            return result[3]
        if len(result) >= 5 and result[4]:
            return result[4]
        return None


bridge: Bridge | None = None
app = FastAPI(title="DLS Mein Essen Bridge")


class SelectMealRequest(BaseModel):
    delivery_date: str
    meal_group_id: str
    meal_id: str
    dish_id: str | None = None


class ClearMealRequest(BaseModel):
    dish_id: str


@app.on_event("startup")
async def on_startup() -> None:
    global bridge
    options = load_options()
    bridge = Bridge(options["customer_number"], options["password"])
    await bridge.start()
    try:
        await bridge.login()
    except Exception:
        # A transient failure here (seen once: net::ERR_NETWORK_CHANGED
        # right after container start) must not crash FastAPI's startup
        # and take the whole add-on down - the watchdog (already running,
        # started inside bridge.start()) will retry on its own cycle.
        _LOGGER.exception("Initial login attempt failed - the watchdog will retry")


@app.get("/health")
async def health() -> dict:
    return {"ready": bool(bridge and bridge.ready)}


@app.get("/food_plan")
async def food_plan(monday: str) -> Any:
    """monday: ISO date (YYYY-MM-DD) of the Monday starting the week."""
    assert bridge is not None
    return await bridge.call("biz.dls.get.caller.food.plan", kwargs={"monday": monday})


@app.get("/cart")
async def cart() -> Any:
    """Current cart entries - used to figure out which dish (if any) is
    currently selected for a given day/meal group."""
    assert bridge is not None
    return await bridge.call("biz.dls.get.caller.cart")


@app.post("/select_meal")
async def select_meal(req: SelectMealRequest) -> Any:
    assert bridge is not None
    kwargs = {
        "deliveryDate": req.delivery_date,
        "mealGroupId": req.meal_group_id,
        "mealId": req.meal_id,
        "amount": 1,
        "device": "web",
        "orderWithoutCart": True,
    }
    if req.dish_id:
        kwargs["dishId"] = req.dish_id
    return await bridge.call("biz.dls.add.caller.order.to.cart", kwargs=kwargs)


@app.post("/clear_meal")
async def clear_meal(req: ClearMealRequest) -> Any:
    assert bridge is not None
    return await bridge.call("biz.dls.remove.caller.cart.entry", kwargs={"dishId": req.dish_id})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8099)
