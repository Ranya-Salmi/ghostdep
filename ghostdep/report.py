"""HTML report generator for `ghostdep report <file>`."""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ghostdep.verdict import Severity, Verdict


# ---------------------------------------------------------------------------
# CSS tokens
# ---------------------------------------------------------------------------

_CSS = """
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #21262d;
  --border: #30363d;
  --text: #c9d1d9;
  --muted: #8b949e;
  --accent: #58a6ff;
  --safe: #3fb950;
  --suspicious: #d29922;
  --blocked: #f85149;
  --mono: ui-monospace, "Cascadia Code", "JetBrains Mono", Consolas, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.6;
  min-height: 100vh;
  padding: 2rem 1rem;
}

.page { max-width: 860px; margin: 0 auto; }

/* ── Header ─────────────────────────────── */
.header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}
.header h1 { font-size: 1.6rem; letter-spacing: -0.02em; }
.header h1 span { color: var(--accent); }
.header .meta { font-size: 0.85rem; color: var(--muted); font-family: var(--mono); }

/* ── Counters ───────────────────────────── */
.counters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}
.counter {
  flex: 1 1 140px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  text-align: center;
}
.counter .num {
  font-size: 2.8rem;
  font-weight: 700;
  line-height: 1;
  display: block;
  margin-bottom: 0.25rem;
}
.counter .label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
.counter.safe .num   { color: var(--safe); }
.counter.suspicious .num { color: var(--suspicious); }
.counter.blocked .num { color: var(--blocked); }

.summary-line {
  font-size: 0.9rem;
  color: var(--muted);
  margin-bottom: 2rem;
}

/* ── Package cards ──────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 1rem;
  overflow: hidden;
}
.card.blocked { border-left: 3px solid var(--blocked); }
.card.suspicious { border-left: 3px solid var(--suspicious); }
.card.safe { border-left: 3px solid var(--safe); }

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  background: var(--surface2);
  flex-wrap: wrap;
}
.pkg-name {
  font-family: var(--mono);
  font-size: 1rem;
  font-weight: 600;
}
.pkg-name.ghost {
  opacity: 0.55;
  text-decoration: line-through;
  text-decoration-color: var(--blocked);
  text-decoration-thickness: 2px;
}
.badge {
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: 1px solid transparent;
}
.badge.safe       { color: var(--safe);       border-color: var(--safe);       }
.badge.suspicious { color: var(--suspicious); border-color: var(--suspicious); }
.badge.blocked    { color: var(--blocked);    border-color: var(--blocked);    }

.card-body { padding: 1rem 1.25rem; }

.findings { list-style: none; margin-bottom: 0.5rem; }
.finding {
  padding: 0.35rem 0;
  font-family: var(--mono);
  font-size: 0.8rem;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
}
.finding:last-child { border-bottom: none; }
.finding-check { color: var(--muted); min-width: 110px; }
.finding-msg { flex: 1; word-break: break-word; }
.finding-sev { padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.7rem; text-transform: uppercase; }
.finding-sev.BLOCKED    { background: rgba(248,81,73,0.15); color: var(--blocked); }
.finding-sev.SUSPICIOUS { background: rgba(210,153,34,0.15); color: var(--suspicious); }
.finding-sev.SAFE       { background: rgba(63,185,80,0.15);  color: var(--safe); }

.suggestion-box {
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  background: rgba(248,81,73,0.08);
  border: 1px solid rgba(248,81,73,0.3);
  border-radius: 6px;
  font-size: 0.875rem;
}
.suggestion-box strong { color: var(--blocked); }
.suggestion-box .alt   { font-family: var(--mono); color: var(--accent); }

.no-findings { font-size: 0.875rem; color: var(--muted); }

/* ── Footer ─────────────────────────────── */
.footer {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 0.8rem;
  color: var(--muted);
}
"""


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {Severity.BLOCKED: 0, Severity.SUSPICIOUS: 1, Severity.SAFE: 2}


def _e(text: str) -> str:
    """HTML-escape a string."""
    return _html.escape(str(text))


def _badge(severity: Severity) -> str:
    cls = severity.value.lower()
    return f'<span class="badge {cls}">{_e(severity.value)}</span>'


def _finding_sev_span(severity: Severity) -> str:
    return f'<span class="finding-sev {_e(severity.value)}">{_e(severity.value)}</span>'


def _card(verdict: Verdict) -> str:
    cls = verdict.overall.value.lower()
    ghost_cls = " ghost" if verdict.overall == Severity.BLOCKED else ""
    name_html = f'<span class="pkg-name{ghost_cls}">{_e(verdict.package)}</span>'

    header = (
        f'<div class="card-header">'
        f'{name_html}'
        f'{_badge(verdict.overall)}'
        f'</div>'
    )

    if not verdict.findings:
        body = '<div class="card-body"><p class="no-findings">No issues found.</p></div>'
    else:
        items = ""
        suggestion_html = ""
        for f in verdict.findings:
            items += (
                f'<li class="finding">'
                f'<span class="finding-check">{_e(f.check)}</span>'
                f'<span class="finding-msg">{_e(f.message)}</span>'
                f'{_finding_sev_span(f.severity)}'
                f'</li>'
            )
            if f.suggestion and verdict.overall == Severity.BLOCKED:
                # Extract alternative name from suggestion
                alt = f.suggestion
                suggestion_html = (
                    f'<div class="suggestion-box">'
                    f'<strong>Use instead:</strong> '
                    f'<span class="alt">{_e(alt)}</span>'
                    f'</div>'
                )

        body = (
            f'<div class="card-body">'
            f'<ul class="findings">{items}</ul>'
            f'{suggestion_html}'
            f'</div>'
        )

    return f'<div class="card {cls}">{header}{body}</div>'


def generate_html(
    verdicts: list[Verdict],
    source_file: str,
    timestamp: Optional[str] = None,
) -> str:
    """Return a self-contained HTML report string."""
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    counts = {Severity.SAFE: 0, Severity.SUSPICIOUS: 0, Severity.BLOCKED: 0}
    for v in verdicts:
        counts[v.overall] += 1

    n_total = len(verdicts)
    n_blocked = counts[Severity.BLOCKED]
    if n_blocked:
        summary_line = f"{n_blocked} of {n_total} package{'s' if n_total != 1 else ''} blocked before install."
    elif counts[Severity.SUSPICIOUS]:
        summary_line = (
            f"{counts[Severity.SUSPICIOUS]} of {n_total} package"
            f"{'s' if n_total != 1 else ''} flagged as suspicious."
        )
    else:
        summary_line = f"All {n_total} package{'s' if n_total != 1 else ''} look safe."

    # Sort: BLOCKED first, then SUSPICIOUS, then SAFE
    sorted_verdicts = sorted(verdicts, key=lambda v: _SEVERITY_ORDER[v.overall])

    counters_html = (
        f'<div class="counters">'
        f'<div class="counter safe">'
        f'<span class="num">{counts[Severity.SAFE]}</span>'
        f'<span class="label">Safe</span>'
        f'</div>'
        f'<div class="counter suspicious">'
        f'<span class="num">{counts[Severity.SUSPICIOUS]}</span>'
        f'<span class="label">Suspicious</span>'
        f'</div>'
        f'<div class="counter blocked">'
        f'<span class="num">{counts[Severity.BLOCKED]}</span>'
        f'<span class="label">Blocked</span>'
        f'</div>'
        f'</div>'
    )

    cards_html = "\n".join(_card(v) for v in sorted_verdicts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GhostDep Report — {_e(source_file)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="header">
    <h1>Ghost<span>Dep</span> Report</h1>
    <div class="meta">{_e(source_file)} &nbsp;·&nbsp; {_e(timestamp)}</div>
  </header>
  {counters_html}
  <p class="summary-line">{_e(summary_line)}</p>
  <section aria-label="Package results">
    {cards_html}
  </section>
  <footer class="footer">
    Checked by GhostDep &nbsp;·&nbsp;
    existence &nbsp;·&nbsp; age &nbsp;·&nbsp; popularity &nbsp;·&nbsp;
    typosquatting &nbsp;·&nbsp; vulnerabilities (OSV)
  </footer>
</div>
</body>
</html>"""
