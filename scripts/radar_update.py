"""Run one GhostDep Radar sweep (used by .github/workflows/radar.yml).

Usage:
    python scripts/radar_update.py
    python scripts/radar_update.py --feed-file fixtures/rss/newest_packages.xml
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ghostdep.radar import update

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-file", help="Read the feed from a local file")
    parser.add_argument("--history", default=str(ROOT / "radar" / "history.jsonl"))
    parser.add_argument("--summary", default=str(ROOT / "docs" / "radar.json"))
    parser.add_argument("--log", default=str(ROOT / "radar" / "log.txt"))
    args = parser.parse_args()

    feed = Path(args.feed_file).read_text(encoding="utf-8") if args.feed_file else None
    record = update(Path(args.history), Path(args.summary), Path(args.log), feed)
    hits = record["lookalikes"]
    print(f"Radar sweep {record['at']}: {record['new']} new packages, "
          f"{len(hits)} possible lookalike(s).")
    for h in hits:
        print(f"  {h['name']}  resembles  {h['resembles']}")


if __name__ == "__main__":
    main()
