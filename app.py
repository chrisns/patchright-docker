"""Drop-in replacement for firecrawl's playwright-service, built on patchright.

Same /scrape contract as ghcr.io/firecrawl/playwright-service, but driven by
patchright (a Playwright fork that does not enable the CDP Runtime domain) and
running real Google Chrome against a persistent profile, so a session carries
cookies and history across requests instead of starting cold every time.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from patchright.async_api import async_playwright

USER_DATA_DIR = os.environ.get("USER_DATA_DIR", "/data/profile")
MAX_CONCURRENT_PAGES = int(os.environ.get("MAX_CONCURRENT_PAGES", "2"))
LOCALE = os.environ.get("LOCALE", "en-GB")
TIMEZONE = os.environ.get("TIMEZONE", "Europe/London")

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    pw = await async_playwright().start()
    # Patchright's own guidance: real chrome channel, headed, no_viewport, and
    # none of the usual stealth flags, each of which is itself distinctive.
    context = await pw.chromium.launch_persistent_context(
        USER_DATA_DIR,
        channel="chrome",
        headless=False,
        no_viewport=True,
        locale=LOCALE,
        timezone_id=TIMEZONE,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    state["pw"] = pw
    state["context"] = context
    state["sem"] = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    try:
        yield
    finally:
        await context.close()
        await pw.stop()


app = FastAPI(lifespan=lifespan)


class ScrapeRequest(BaseModel):
    url: str
    wait_after_load: int = 0
    timeout: int = 60000
    headers: dict | None = None
    check_selector: str | None = None


@app.get("/health")
async def health():
    return {"ok": True, "pages": len(state["context"].pages)}


@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    async with state["sem"]:
        page = await state["context"].new_page()
        try:
            if req.headers:
                await page.set_extra_http_headers(req.headers)
            status, error = None, None
            try:
                response = await page.goto(
                    req.url, timeout=req.timeout, wait_until="domcontentloaded"
                )
                status = response.status if response else None
            except Exception as exc:  # navigation failed; still return what loaded
                error = str(exc)

            if req.wait_after_load:
                await page.wait_for_timeout(req.wait_after_load)

            if req.check_selector:
                try:
                    await page.wait_for_selector(req.check_selector, timeout=req.timeout)
                except Exception as exc:
                    error = f"selector not found: {exc}"

            content = await page.content()
            return {"content": content, "pageStatusCode": status, "pageError": error}
        finally:
            await page.close()


class EvalRequest(BaseModel):
    url: str
    script: str
    wait_after_load: int = 0
    timeout: int = 60000


@app.post("/evaluate")
async def evaluate(req: EvalRequest):
    """Load a page, then run JS inside it.

    Requests issued from in-page JS inherit Chrome's own TLS stack, cookie jar
    and header ordering, which a node-side fetch does not.
    """
    async with state["sem"]:
        page = await state["context"].new_page()
        try:
            response = await page.goto(
                req.url, timeout=req.timeout, wait_until="domcontentloaded"
            )
            if req.wait_after_load:
                await page.wait_for_timeout(req.wait_after_load)
            result = await page.evaluate(req.script)
            return {
                "result": result,
                "pageStatusCode": response.status if response else None,
            }
        finally:
            await page.close()
