"""Playwright-based renderer for SPA job boards (Glints, Kalibrr, WWR)."""
import time
from typing import Optional
from playwright.sync_api import sync_playwright


def render(url: str, wait_for: str = "body", wait_ms: int = 4000,
           ua: Optional[str] = None) -> str:
    """Load SPA page, wait for JS render, return HTML. Auto-closes browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=ua or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector(wait_for, timeout=wait_ms)
        except Exception:
            pass
        time.sleep(2)
        html = page.content()
        browser.close()
        return html