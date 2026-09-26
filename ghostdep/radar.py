"""GhostDep Radar: continuous monitoring of newly published PyPI packages.

Each sweep reads PyPI's newest-packages feed, keeps only names not seen in
earlier sweeps, runs the radar lookalike check on them, and appends a record
to a JSONL history file. A compact summary is written as JSON for the landing
page (docs/radar.json).

Lookalikes are *possible* impersonations of popular packages. They are not
necessarily malicious and should be reviewed before acting.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ghostdep.scan_new import _fetch_rss, check_new_packages, parse_rss

RECENT_SWEEPS_IN_SUMMARY = 48  # ~24 h at one sweep every 30 minutes


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_history(path: Path) -> list[dict]:
    """Return all sweep records from a JSONL history file (empty if missing)."""
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def run_sweep(
    history: list[dict],
    feed_xml: str,
    now: Optional[str] = None,
    checker: Callable[[list[str]], list[tuple[str, str]]] = check_new_packages,
) -> dict:
    """Run one sweep over *feed_xml* and return the new history record."""
    seen = {name.lower() for rec in history for name in rec.get("names", [])}
    in_feed = list(dict.fromkeys(parse_rss(feed_xml)))  # dedupe, keep order
    new_names = [n for n in in_feed if n.lower() not in seen]
    lookalikes = checker(new_names) if new_names else []
    return {
        "at": now or _now_iso(),
        "in_feed": len(in_feed),
        "new": len(new_names),
        "names": new_names,
        "lookalikes": [{"name": n, "resembles": p} for n, p in lookalikes],
    }


def summarize(history: list[dict], now: Optional[str] = None) -> dict:
    """Build the landing-page summary from the full sweep history."""
    first_seen: dict[str, dict] = {}
    for rec in history:
        for hit in rec.get("lookalikes", []):
            key = hit["name"].lower()
            if key not in first_seen:
                first_seen[key] = {**hit, "first_seen": rec["at"]}
    return {
        "generated_at": now or _now_iso(),
        "first_sweep": history[0]["at"] if history else None,
        "last_sweep": history[-1]["at"] if history else None,
        "sweeps": len(history),
        "packages_checked": sum(rec.get("new", 0) for rec in history),
        "lookalikes": sorted(first_seen.values(), key=lambda h: h["first_seen"],
                             reverse=True),
        "recent_sweeps": [
            {"at": r["at"], "new": r.get("new", 0),
             "lookalikes": len(r.get("lookalikes", []))}
            for r in history[-RECENT_SWEEPS_IN_SUMMARY:]
        ],
    }


def log_line(record: dict) -> str:
    """Human-readable line for radar/log.txt."""
    hits = record["lookalikes"]
    head = f"=== {record['at']} === {record['new']} new of {record['in_feed']} in feed"
    if not hits:
        return f"{head}; no lookalikes.\n"
    body = "".join(f"  {h['name']}  resembles  {h['resembles']}\n" for h in hits)
    return f"{head}; {len(hits)} possible lookalike(s):\n{body}"


def update(
    history_path: Path,
    summary_path: Path,
    log_path: Optional[Path] = None,
    feed_xml: Optional[str] = None,
) -> dict:
    """Run a sweep, append it to the history, and rewrite the summary."""
    history = load_history(history_path)
    record = run_sweep(history, feed_xml if feed_xml is not None else _fetch_rss())
    history.append(record)

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summarize(history), indent=2) + "\n",
                            encoding="utf-8")

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(log_line(record))
    return record
