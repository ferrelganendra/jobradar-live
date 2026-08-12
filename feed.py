"""RSS 2.0 feed generator (no heavy deps, importable standalone)."""
import html
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def _fmt_rfc822(ts):
    """'2026-08-12 13:14:24' (UTC, SQLite datetime) -> RFC-822 pubDate."""
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def render(jobs: list[dict]) -> str:
    """Build RSS XML string from latest deduped jobs (most recent 50)."""
    jobs = sorted(jobs, key=lambda j: j.get("created_at") or "", reverse=True)[:50]
    items = []
    for j in jobs:
        desc_raw = html.unescape(j.get("description") or "")
        desc_plain = " ".join(desc_raw.split())[:400]
        desc = escape(desc_plain)
        items.append(
            "    <item>\n"
            f"      <title>{escape(j.get('title') or '')}</title>\n"
            f"      <link>{escape(j.get('url') or '')}</link>\n"
            f"      <guid isPermaLink=\"false\">{j.get('id', '')}</guid>\n"
            f"      <pubDate>{_fmt_rfc822(j.get('created_at'))}</pubDate>\n"
            f"      <description>{desc}</description>\n"
            f"      <category>{escape(j.get('industry') or '')}</category>\n"
            f"      <job:remote>{'true' if j.get('remote_ok') else 'false'}</job:remote>\n"
            f"      <job:salary>{escape(j.get('salary') or '')}</job:salary>\n"
            f"      <job:location>{escape(j.get('location') or '')}</job:location>\n"
            f"      <job:company>{escape(j.get('company') or '')}</job:company>\n"
            "    </item>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:job="http://jobradar.id/ns/job">\n'
        "  <channel>\n"
        "    <title>JobRadar LIVE Loker</title>\n"
        "    <link>https://jobradar.pages.dev/</link>\n"
        "    <description>Loker Indonesia + remote terbaru dari JobRadar</description>\n"
        "    <language>id</language>\n"
        f"    <lastBuildDate>{_fmt_rfc822(datetime.utcnow().isoformat(' '))}</lastBuildDate>\n"
        + "".join(items)
        + "  </channel>\n</rss>\n"
    )


def write(jobs: list[dict], path: str = "") -> str:
    """Write feed to OUT/feed.xml (or given path). Returns path."""
    dst = path or os.path.join(OUT, "feed.xml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f:
        f.write(render(jobs))
    return dst