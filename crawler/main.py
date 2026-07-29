"""
Curator engine crawler.

Reads sources.yaml, pulls each RSS/Atom feed, extracts a summary (publisher's
own description if usable, otherwise a free local extractive summary),
de-duplicates against what's already stored, and writes one JSON file per
category into docs/data/. GitHub Pages serves docs/ as the site, so the data
this script writes IS what the PWA reads — no server, no database.

Safe by design: a single dead/slow/malformed feed is logged and skipped, it
never aborts the whole run.
"""

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

from summarize import best_summary, clean_html

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.yaml"
DATA_DIR = ROOT / "docs" / "data"
MAX_ITEMS_PER_CATEGORY = 150   # keep JSON files small enough for a phone
FETCH_TIMEOUT = 15             # seconds, per feed

feedparser.USER_AGENT = "curator-engine/1.0 (personal RSS reader)"


def entry_id(link: str, title: str) -> str:
    return hashlib.sha1(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def load_sources() -> dict:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_existing(category: str) -> list:
    path = DATA_DIR / f"{category}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("items", [])
    except (json.JSONDecodeError, OSError):
        return []


def fetch_feed(url: str):
    """Returns a parsed feed or None on failure. Never raises."""
    try:
        parsed = feedparser.parse(url, agent=feedparser.USER_AGENT)
        if parsed.bozo and not parsed.entries:
            return None
        return parsed
    except Exception as e:  # noqa: BLE001 - crawler must never crash on one bad source
        print(f"    ! fetch failed: {e}")
        return None


def entry_published(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def process_category(category: str, sources: list) -> list:
    print(f"\n[{category}]")
    existing = load_existing(category)
    seen_ids = {item["id"] for item in existing}
    new_items = []

    for source in sources:
        name, url = source["name"], source["url"]
        print(f"  fetching {name} ...")
        parsed = fetch_feed(url)
        if not parsed or not parsed.entries:
            print("    ! no entries, skipping")
            continue

        for entry in parsed.entries:
            link = getattr(entry, "link", "")
            title = clean_html(getattr(entry, "title", "")).strip()
            if not link or not title:
                continue

            iid = entry_id(link, title)
            if iid in seen_ids:
                continue

            raw_summary = getattr(entry, "summary", "") or ""
            body = ""
            if hasattr(entry, "content") and entry.content:
                body = entry.content[0].get("value", "")

            summary = best_summary(raw_summary, body, max_sentences=3)

            new_items.append({
                "id": iid,
                "title": title,
                "link": link,
                "source": name,
                "category": category,
                "summary": summary,
                "published": entry_published(entry),
                "fetched": datetime.now(timezone.utc).isoformat(),
            })
            seen_ids.add(iid)

    print(f"  + {len(new_items)} new item(s)")
    combined = new_items + existing
    combined.sort(key=lambda x: x["published"], reverse=True)
    return combined[:MAX_ITEMS_PER_CATEGORY]


def write_category(category: str, items: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{category}.json"
    payload = {
        "category": category,
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_index(all_items_by_category: dict) -> None:
    """A lightweight combined index so the PWA can show an 'All' view without
    loading every category file up front."""
    summary = []
    total = 0
    for category, items in all_items_by_category.items():
        total += len(items)
        summary.append({"category": category, "count": len(items)})
    path = DATA_DIR / "index.json"
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total_items": total,
        "categories": summary,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    sources_by_category = load_sources()
    if not sources_by_category:
        print("No sources found in sources.yaml — nothing to do.")
        sys.exit(0)

    all_items = {}
    for category, sources in sources_by_category.items():
        items = process_category(category, sources)
        write_category(category, items)
        all_items[category] = items

    write_index(all_items)
    print("\nDone.")


if __name__ == "__main__":
    main()
