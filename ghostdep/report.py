"""Premium HTML report generator for `ghostdep report <file>`.

Design spec:
  --bg: #0B0D10        page background
  --surface: #12151A   panels
  --surface-2: #181C22 raised elements
  --border: #232931
  --text: #E6EDF3
  --muted: #8B949E
  --accent: #7FE3F0    spectral cyan
  --safe: #3FB950
  --suspicious: #D29922
  --blocked: #F85149

Ghost metaphor: BLOCKED packages have ghost styling — dashed border, reduced opacity,
struck-through name. Real packages are rendered solid.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ghostdep.verdict import Severity, Verdict


# ---------------------------------------------------------------------------
# Inline SVG icons (verdict shape identifiers — never rely on color alone)
# ---------------------------------------------------------------------------

# Shield check — SAFE
_ICON_SAFE = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" '
    'aria-hidden="true" style="vertical-align:-2px">'
    '<path d="M8 1L2 3.5V8c0 3 2.5 5.2 6 6.5C11.5 13.2 14 11 14 8V3.5L8 1z" '
    'stroke="#3FB950" stroke-width="1.5" fill="none"/>'
    '<path d="M5.5 8l2 2 3-3" stroke="#3FB950" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

# Warning triangle — SUSPICIOUS
_ICON_SUSPICIOUS = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" '
    'aria-hidden="true" style="vertical-align:-2px">'
    '<path d="M8 2L1.5 13.5h13L8 2z" stroke="#D29922" stroke-width="1.5" '
    'fill="none" stroke-linejoin="round"/>'
    '<line x1="8" y1="6.5" x2="8" y2="9.5" stroke="#D29922" stroke-width="1.5" '
    'stroke-linecap="round"/>'
    '<circle cx="8" cy="11.5" r="0.75" fill="#D29922"/>'
    '</svg>'
)

# Ghost — BLOCKED (dashed outline circle with hollow centre)
_ICON_BLOCKED = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" '
    'aria-hidden="true" style="vertical-align:-2px">'
    '<circle cx="8" cy="8" r="6" stroke="#F85149" stroke-width="1.5" '
    'stroke-dasharray="3 2"/>'
    '<line x1="5.5" y1="5.5" x2="10.5" y2="10.5" stroke="#F85149" '
    'stroke-width="1.5" stroke-linecap="round"/>'
    '<line x1="10.5" y1="5.5" x2="5.5" y2="10.5" stroke="#F85149" '
    'stroke-width="1.5" stroke-linecap="round"/>'
    '</svg>'
)

_ICONS = {
    Severity.SAFE: _ICON_SAFE,
    Severity.SUSPICIOUS: _ICON_SUSPICIOUS,
    Severity.BLOCKED: _ICON_BLOCKED,
}

# Check-level mini indicators
_MINI_PASS = (
    '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" '
    'aria-label="pass" style="vertical-align:-1px">'
    '<circle cx="5" cy="5" r="4" fill="rgba(63,185,80,0.18)"/>'
    '<path d="M3 5l1.5 1.5L7 3.5" stroke="#3FB950" stroke-width="1.2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)
_MINI_WARN = (
    '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" '
    'aria-label="suspicious" style="vertical-align:-1px">'
    '<circle cx="5" cy="5" r="4" fill="rgba(210,153,34,0.18)"/>'
    '<line x1="5" y1="3" x2="5" y2="6" stroke="#D29922" stroke-width="1.2" '
    'stroke-linecap="round"/>'
    '<circle cx="5" cy="7.2" r="0.6" fill="#D29922"/>'
    '</svg>'
)
_MINI_FAIL = (
    '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" '
    'aria-label="blocked" style="vertical-align:-1px">'
    '<circle cx="5" cy="5" r="4" fill="rgba(248,81,73,0.18)"/>'
    '<line x1="3.5" y1="3.5" x2="6.5" y2="6.5" stroke="#F85149" stroke-width="1.2" '
    'stroke-linecap="round"/>'
    '<line x1="6.5" y1="3.5" x2="3.5" y2="6.5" stroke="#F85149" stroke-width="1.2" '
    'stroke-linecap="round"/>'
    '</svg>'
)

_MINI_ICONS = {
    Severity.SAFE: _MINI_PASS,
    Severity.SUSPICIOUS: _MINI_WARN,
    Severity.BLOCKED: _MINI_FAIL,
}

# All 5 check names in canonical order
_CHECK_ORDER = ["existence", "age", "popularity", "typosquat", "vulnerabilities"]


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
/* ── Design tokens ─────────────────────── */
:root {
  --bg:        #0B0D10;
  --surface:   #12151A;
  --surface-2: #181C22;
  --border:    #232931;
  --text:      #E6EDF3;
  --muted:     #8B949E;
  --accent:    #7FE3F0;
  --safe:      #3FB950;
  --suspicious:#D29922;
  --blocked:   #F85149;
  --mono: ui-monospace, "Cascadia Code", "JetBrains Mono", Consolas, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", Inter, Roboto, sans-serif;
  --space: 8px;
}

/* ── Reset ──────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Base ───────────────────────────────── */
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.6;
  min-height: 100vh;
  padding: calc(var(--space)*4) calc(var(--space)*2);
}

/* ── Focus ──────────────────────────────── */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 2px;
}

/* ── Layout ─────────────────────────────── */
.page { max-width: 860px; margin: 0 auto; }

/* ── Header ─────────────────────────────── */
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: calc(var(--space)*2);
  margin-bottom: calc(var(--space)*4);
  padding-bottom: calc(var(--space)*2);
  border-bottom: 1px solid var(--border);
}
.wordmark {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--text);
}
.wordmark .dot { color: var(--accent); }
.header-meta {
  text-align: right;
  font-size: 0.8rem;
  font-family: var(--mono);
  color: var(--muted);
  line-height: 1.8;
}
.header-meta strong { color: var(--text); font-weight: 500; }

/* ── Counters ───────────────────────────── */
.counters {
  display: flex;
  gap: calc(var(--space)*2);
  margin-bottom: calc(var(--space)*3);
  flex-wrap: wrap;
}
.counter {
  flex: 1 1 160px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: calc(var(--space)*3) calc(var(--space)*3);
  display: flex;
  align-items: center;
  gap: calc(var(--space)*2);
}
.counter-num {
  font-size: 3rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.03em;
  min-width: 2.5ch;
  text-align: right;
}
.counter-info .label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  display: block;
}
.counter.safe       .counter-num { color: var(--safe); }
.counter.suspicious .counter-num { color: var(--suspicious); }
.counter.blocked    .counter-num { color: var(--blocked); }

.summary-sentence {
  font-size: 0.9rem;
  color: var(--muted);
  margin-bottom: calc(var(--space)*4);
  padding-left: 2px;
}

/* ── Package cards ──────────────────────── */
.cards { display: flex; flex-direction: column; gap: calc(var(--space)*2); }

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

/* Ghost styling for BLOCKED */
.card.ghost {
  border-style: dashed;
  border-color: rgba(248,81,73,0.45);
  opacity: 0.88;
}

.card-header {
  display: flex;
  align-items: center;
  gap: calc(var(--space)*2);
  padding: calc(var(--space)*2) calc(var(--space)*3);
  background: var(--surface-2);
  flex-wrap: wrap;
}

.pkg-name {
  font-family: var(--mono);
  font-size: 1rem;
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow-wrap: break-word;
}
.card.ghost .pkg-name {
  text-decoration: line-through;
  text-decoration-color: var(--blocked);
  text-decoration-thickness: 2px;
  opacity: 0.65;
}

/* Verdict badge */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0.2rem 0.65rem;
  border-radius: 5px;
  font-size: 0.73rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border: 1px solid transparent;
  white-space: nowrap;
}
.badge.safe       { color: var(--safe);       border-color: rgba(63,185,80,0.35);  background: rgba(63,185,80,0.08); }
.badge.suspicious { color: var(--suspicious); border-color: rgba(210,153,34,0.35); background: rgba(210,153,34,0.08); }
.badge.blocked    { color: var(--blocked);    border-color: rgba(248,81,73,0.35);  background: rgba(248,81,73,0.08); }

/* Check indicators row */
.check-row {
  display: flex;
  gap: calc(var(--space)*1);
  align-items: center;
  flex-wrap: wrap;
}
.check-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--muted);
  white-space: nowrap;
}

/* Card body */
.card-body { padding: calc(var(--space)*2) calc(var(--space)*3); }

.findings { list-style: none; margin-bottom: 0; }
.finding {
  display: grid;
  grid-template-columns: 100px 1fr auto;
  gap: calc(var(--space)*1) calc(var(--space)*2);
  padding: calc(var(--space)*1) 0;
  font-size: 0.8rem;
  border-bottom: 1px solid var(--border);
  align-items: baseline;
}
.finding:last-child { border-bottom: none; }
.finding-check { font-family: var(--mono); color: var(--muted); }
.finding-msg   { font-family: var(--mono); color: var(--text); word-break: break-word; }
.finding-sev {
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
}
.finding-sev.BLOCKED    { background: rgba(248,81,73,0.15); color: var(--blocked); }
.finding-sev.SUSPICIOUS { background: rgba(210,153,34,0.15); color: var(--suspicious); }
.finding-sev.SAFE       { background: rgba(63,185,80,0.12); color: var(--safe); }

/* Use-instead box */
.suggestion-box {
  margin-top: calc(var(--space)*2);
  padding: calc(var(--space)*2) calc(var(--space)*2);
  background: rgba(248,81,73,0.06);
  border: 1px solid rgba(248,81,73,0.28);
  border-radius: 7px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: calc(var(--space)*1);
  flex-wrap: wrap;
}
.suggestion-label { color: var(--muted); }
.suggestion-value { font-family: var(--mono); color: var(--accent); font-weight: 600; }

/* No-findings */
.no-findings { font-size: 0.85rem; color: var(--muted); }

/* ── Footer ─────────────────────────────── */
.footer {
  margin-top: calc(var(--space)*6);
  padding-top: calc(var(--space)*2);
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 0.78rem;
  color: var(--muted);
  line-height: 2;
}
.footer a { color: var(--accent); text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* ── Motion ─────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .card {
    animation: fadeIn 200ms ease both;
  }
  .card:nth-child(1) { animation-delay:   0ms; }
  .card:nth-child(2) { animation-delay:  30ms; }
  .card:nth-child(3) { animation-delay:  60ms; }
  .card:nth-child(4) { animation-delay:  90ms; }
  .card:nth-child(5) { animation-delay: 120ms; }
  .card:nth-child(n+6) { animation-delay: 150ms; }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
}

/* ── Responsive ─────────────────────────── */
@media (max-width: 500px) {
  .finding { grid-template-columns: 80px 1fr; }
  .finding-sev { grid-column: 2; }
}
"""


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {Severity.BLOCKED: 0, Severity.SUSPICIOUS: 1, Severity.SAFE: 2}


def _e(text: str) -> str:
    return _html.escape(str(text))


def _badge(severity: Severity) -> str:
    cls = severity.value.lower()
    icon = _ICONS[severity]
    return (
        f'<span class="badge {cls}" role="img" '
        f'aria-label="{_e(severity.value)}">'
        f'{icon}&nbsp;{_e(severity.value)}'
        f'</span>'
    )


def _check_row(findings_by_check: dict[str, Severity]) -> str:
    """Render compact pass/fail indicators for each of the 5 checks."""
    pills = []
    for check in _CHECK_ORDER:
        sev = findings_by_check.get(check, Severity.SAFE)
        icon = _MINI_ICONS[sev]
        pills.append(
            f'<span class="check-pill">{icon}&nbsp;{_e(check)}</span>'
        )
    return f'<div class="check-row">{"".join(pills)}</div>'


def _card(verdict: Verdict) -> str:
    ghost_cls = " ghost" if verdict.overall == Severity.BLOCKED else ""
    name_html = f'<span class="pkg-name">{_e(verdict.package)}</span>'

    # Build findings-by-check map for the check indicator row
    by_check: dict[str, Severity] = {}
    for f in verdict.findings:
        existing = by_check.get(f.check)
        if existing is None or _SEVERITY_ORDER[f.severity] < _SEVERITY_ORDER[existing]:
            by_check[f.check] = f.severity

    header = (
        f'<div class="card-header">'
        f'{name_html}'
        f'{_badge(verdict.overall)}'
        f'{_check_row(by_check)}'
        f'</div>'
    )

    if not verdict.findings:
        body = (
            '<div class="card-body">'
            '<p class="no-findings">All checks passed.</p>'
            '</div>'
        )
    else:
        rows = ""
        suggestion_html = ""
        for f in verdict.findings:
            rows += (
                f'<li class="finding">'
                f'<span class="finding-check">{_e(f.check)}</span>'
                f'<span class="finding-msg">{_e(f.message)}</span>'
                f'<span class="finding-sev {_e(f.severity.value)}">'
                f'{_e(f.severity.value)}</span>'
                f'</li>'
            )
            if f.suggestion and verdict.overall == Severity.BLOCKED and not suggestion_html:
                suggestion_html = (
                    f'<div class="suggestion-box">'
                    f'<span class="suggestion-label">Use instead:</span>'
                    f'<span class="suggestion-value">{_e(f.suggestion)}</span>'
                    f'</div>'
                )

        body = (
            f'<div class="card-body">'
            f'<ul class="findings">{rows}</ul>'
            f'{suggestion_html}'
            f'</div>'
        )

    return f'<article class="card{ghost_cls}" aria-label="{_e(verdict.package)}">{header}{body}</article>'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_html(
    verdicts: list[Verdict],
    source_file: str,
    timestamp: Optional[str] = None,
) -> str:
    """Return a fully self-contained HTML report string."""
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    counts = {Severity.SAFE: 0, Severity.SUSPICIOUS: 0, Severity.BLOCKED: 0}
    for v in verdicts:
        counts[v.overall] += 1

    n_total = len(verdicts)
    n_blocked = counts[Severity.BLOCKED]
    if n_blocked:
        summary = (
            f"{n_blocked} of {n_total} package"
            f"{'s' if n_total != 1 else ''} blocked before install."
        )
    elif counts[Severity.SUSPICIOUS]:
        summary = (
            f"{counts[Severity.SUSPICIOUS]} of {n_total} package"
            f"{'s' if n_total != 1 else ''} flagged suspicious — review before installing."
        )
    else:
        summary = f"All {n_total} package{'s' if n_total != 1 else ''} look safe."

    sorted_verdicts = sorted(verdicts, key=lambda v: _SEVERITY_ORDER[v.overall])

    counters_html = (
        f'<div class="counters" role="region" aria-label="Verdict summary">'
        f'<div class="counter safe" aria-label="{counts[Severity.SAFE]} safe">'
        f'<span class="counter-num" aria-hidden="true">{counts[Severity.SAFE]}</span>'
        f'<div class="counter-info"><span class="label">Safe</span></div>'
        f'</div>'
        f'<div class="counter suspicious" aria-label="{counts[Severity.SUSPICIOUS]} suspicious">'
        f'<span class="counter-num" aria-hidden="true">{counts[Severity.SUSPICIOUS]}</span>'
        f'<div class="counter-info"><span class="label">Suspicious</span></div>'
        f'</div>'
        f'<div class="counter blocked" aria-label="{counts[Severity.BLOCKED]} blocked">'
        f'<span class="counter-num" aria-hidden="true">{counts[Severity.BLOCKED]}</span>'
        f'<div class="counter-info"><span class="label">Blocked</span></div>'
        f'</div>'
        f'</div>'
    )

    cards_html = "\n".join(_card(v) for v in sorted_verdicts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="GhostDep security report for {_e(source_file)}">
<title>GhostDep Report — {_e(source_file)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="header">
    <h1 class="wordmark">Ghost<span class="dot">.</span>Dep</h1>
    <div class="header-meta">
      <strong>{_e(source_file)}</strong><br>
      {_e(timestamp)}
    </div>
  </header>

  {counters_html}
  <p class="summary-sentence">{_e(summary)}</p>

  <main>
    <div class="cards" role="list">
      {cards_html}
    </div>
  </main>

  <footer class="footer">
    Checked by GhostDep &nbsp;·&nbsp;
    existence &nbsp;·&nbsp; age &nbsp;·&nbsp; popularity &nbsp;·&nbsp;
    typosquatting &nbsp;·&nbsp; vulnerabilities (OSV)
  </footer>
</div>
</body>
</html>"""
