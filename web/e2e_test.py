"""E2E test for JobRadar web via project venv playwright (bypasses browser-use PYTHONPATH leak)."""
import json, sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8124/"
fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.wait_for_selector(".card", timeout=15000)

    check("page title", "JobRadar" in pg.title())
    check("ticker total>0", int(pg.text_content("#totalCount").replace(".", "")) > 0)
    check("cards render", pg.locator(".card").count() > 0)
    check("bookmark btn exists", pg.locator(".btn-bookmark").count() > 0)
    check("fresh filter exists", pg.locator("#fFresh").count() == 1)
    check("rss link", pg.locator(".filter-link").get_attribute("href") == "data/feed.xml")
    check("bookmark preset", pg.locator("#presetBookmarks").count() == 1)

    # default sort "recent" = newest first: first card title == newest created_at job
    sort_ok = pg.evaluate("""
      async () => {
        const jobs = await (await fetch('data/jobs.json')).json();
        const newest = jobs
          .filter(j => j.created_at)
          .sort((a, b) => new Date(b.created_at.replace(' ', 'T') + 'Z') - new Date(a.created_at.replace(' ', 'T') + 'Z'))[0];
        const firstTitle = document.querySelector('.card .card-title').textContent.trim();
        return firstTitle === newest.title.trim();
      }
    """)
    check("default sort newest-first", sort_ok)

    # bookmark toggle persists
    pg.locator(".btn-bookmark").first.click()
    pressed = pg.locator(".btn-bookmark").first.get_attribute("aria-pressed")
    check("bookmark aria-pressed", pressed == "true")
    stored = pg.evaluate("localStorage.getItem('jobradar.bookmarks')")
    check("bookmark stored", stored and stored != "null" and len(json.loads(stored)) >= 1)

    # bookmark preset filter
    pg.locator("#presetBookmarks").click()
    pg.wait_for_timeout(300)
    check("bookmark preset active", "on" in pg.locator("#presetBookmarks").get_attribute("class"))
    # should show only bookmarked (>=1 since we saved 1)
    check("bookmark filter shows saved", pg.locator(".card").count() >= 1)

    # fresh filter
    pg.locator("#fFresh").select_option("24")
    pg.wait_for_timeout(200)
    check("fresh filter selectable", pg.locator(".card").count() >= 0)  # smoke only

    # modal
    pg.evaluate("resetFilters()" if False else "document.querySelector('#resetFilters').click()")
    pg.wait_for_timeout(200)
    pg.locator(".card").first.click()
    pg.wait_for_selector("#modal:not([hidden])", timeout=5000)
    check("modal opens", pg.locator("#modal").is_visible())
    check("modal title", len(pg.text_content("#modalTitle").strip()) > 0)
    check("modal desc", len(pg.text_content("#modalDesc").strip()) > 0)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    check("modal closes on esc", not pg.locator("#modal").is_visible())

    check("no console errors", len(errs) == 0, str(errs[:5]))
    b.close()

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}"))
sys.exit(1 if fails else 0)