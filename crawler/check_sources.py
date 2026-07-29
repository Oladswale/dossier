"""
Run this locally after editing sources.yaml:

    python crawler/check_sources.py

Reports which feeds are alive and parseable, and which are dead/broken, so
you can prune the list before pushing. Doesn't write anything.
"""

import sys
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.yaml"


def main():
    sources_by_category = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    ok, bad = 0, []

    for category, sources in sources_by_category.items():
        print(f"\n[{category}]")
        for source in sources:
            name, url = source["name"], source["url"]
            parsed = feedparser.parse(url)
            if parsed.entries:
                print(f"  OK   {name} ({len(parsed.entries)} entries)")
                ok += 1
            else:
                print(f"  DEAD {name} -> {url}")
                bad.append((category, name, url))

    print(f"\n{ok} feed(s) OK, {len(bad)} dead.")
    if bad:
        print("\nConsider removing or replacing these in sources.yaml:")
        for category, name, url in bad:
            print(f"  - [{category}] {name}: {url}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
