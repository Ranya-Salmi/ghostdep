"""Tests for the GhostDep Radar sweep and summary."""
from __future__ import annotations

import json
from pathlib import Path

from ghostdep.radar import load_history, log_line, run_sweep, summarize, update

FEED = (Path(__file__).parent.parent / "fixtures" / "rss" /
        "newest_packages.xml").read_text(encoding="utf-8")


def _fake_checker(names):
    table = {"reqeusts": "requests", "numppy": "numpy"}
    return [(n, table[n]) for n in names if n in table]


def test_first_sweep_checks_every_name():
    rec = run_sweep([], FEED, now="2026-09-26T12:00:00Z", checker=_fake_checker)
    assert rec["new"] == rec["in_feed"] > 0
    assert {h["name"] for h in rec["lookalikes"]} == {"reqeusts", "numppy"}


def test_second_sweep_skips_names_already_seen():
    first = run_sweep([], FEED, now="t1", checker=_fake_checker)
    second = run_sweep([first], FEED, now="t2", checker=_fake_checker)
    assert second["new"] == 0
    assert second["lookalikes"] == []


def test_summary_counts_unique_packages_and_first_seen():
    first = run_sweep([], FEED, now="2026-09-26T12:00:00Z", checker=_fake_checker)
    second = run_sweep([first], FEED, now="2026-09-26T12:30:00Z",
                       checker=_fake_checker)
    s = summarize([first, second], now="2026-09-26T12:31:00Z")
    assert s["sweeps"] == 2
    assert s["packages_checked"] == first["new"]
    assert s["first_sweep"] == "2026-09-26T12:00:00Z"
    assert s["last_sweep"] == "2026-09-26T12:30:00Z"
    assert {h["name"] for h in s["lookalikes"]} == {"reqeusts", "numppy"}
    assert all(h["first_seen"] == "2026-09-26T12:00:00Z" for h in s["lookalikes"])
    assert len(s["recent_sweeps"]) == 2


def test_empty_history_summary():
    s = summarize([], now="x")
    assert s["sweeps"] == 0 and s["packages_checked"] == 0
    assert s["first_sweep"] is None and s["lookalikes"] == []


def test_update_writes_history_summary_and_log(tmp_path):
    hist, summ, log = tmp_path / "h.jsonl", tmp_path / "s.json", tmp_path / "log.txt"
    update(hist, summ, log, feed_xml=FEED)
    update(hist, summ, log, feed_xml=FEED)
    assert len(load_history(hist)) == 2
    data = json.loads(summ.read_text(encoding="utf-8"))
    assert data["sweeps"] == 2
    assert sum(l.startswith("===") for l in log.read_text(encoding="utf-8").splitlines()) == 2


def test_real_checker_flags_known_lookalikes(tmp_path):
    rec = run_sweep([], FEED, now="t")
    flagged = {h["name"] for h in rec["lookalikes"]}
    assert "reqeusts" in flagged


def test_log_line_formats():
    quiet = {"at": "t", "new": 3, "in_feed": 40, "lookalikes": []}
    assert "no lookalikes" in log_line(quiet)
    loud = {"at": "t", "new": 3, "in_feed": 40,
            "lookalikes": [{"name": "reqeusts", "resembles": "requests"}]}
    assert "reqeusts  resembles  requests" in log_line(loud)
