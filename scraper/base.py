"""Base scraper interface + shared anti-ban helpers."""
import time
import random
import requests

UA_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
]


def random_ua() -> str:
    return random.choice(UA_LIST)


def polite_delay(lo: float = 1.0, hi: float = 3.0) -> None:
    """Random delay between requests to avoid rate-limit bans."""
    time.sleep(random.uniform(lo, hi))


def fetch(url: str, timeout: int = 20, retries: int = 3, **kw) -> requests.Response:
    """GET with UA rotation + retry/backoff."""
    kw.setdefault("headers", {"User-Agent": random_ua()})
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        delay = 2 ** attempt + random.uniform(0, 1)
        time.sleep(delay)
    r.raise_for_status()
    return r


class BaseScraper:
    source = "base"

    def fetch_jobs(self) -> list[dict]:
        raise NotImplementedError