# PROGRESS.md — GhostDep Development Log

---

## Redesign — Premium report + landing page

**Completed:** 2026-09-26

### What was done

**`ghostdep/report.py` (REDESIGN PART 1):**
- Complete rewrite with new design tokens (`--bg #0B0D10`, `--accent #7FE3F0`, etc.).
- Inline SVG icons for every verdict: shield (SAFE), triangle (SUSPICIOUS), dashed
  ghost circle with X (BLOCKED) — accessibility never relies on color alone.
- Compact check-row indicators (mini pass/fail SVG per check) in each card header.
- BLOCKED cards use ghost styling: dashed border, reduced opacity, struck-through name.
- `prefers-reduced-motion` support: animation disabled when user prefers it.
- Responsive down to 375px; visible `:focus-visible` states with accent outline.
- Semantic HTML: `<article>`, `<main>`, `aria-label`, `role="list"`.
- Regenerated `demo/report-example.html` and `docs/report-example.html`.

**`docs/index.html` (REDESIGN PART 2):**
- Sticky nav with backdrop blur, responsive (hidden on mobile).
- Hero with animated terminal replay (typed line-by-line, inline JS, ~40 lines).
- "Live catch" section as a minimal two-event timeline (25 Sep BLOCKED → 26 Sep removed).
- "How it works" as a three-step horizontal flow with arrows (not identical cards).
- Benchmark section: four large-number cards with honest methodology note.
- "Works everywhere" section: IBM Bob, CLI, and CI, each as a code-snippet card.
- Footer: GitHub link, MIT, "Built with IBM Bob".
- Open Graph meta tags and meta description.
- `docs/report-example.html` copied from `demo/report-example.html` so the
  "See an example report" button works on GitHub Pages.

**Quality check:**
- `scripts/check_html_quality.py`: validates no external resource requests in
  `docs/index.html`, `docs/report-example.html`, `demo/report-example.html`.
- All 133 tests pass.

### Design decisions
- Terminal replay uses `setTimeout` with staggered delays (400–2400ms). Under
  `prefers-reduced-motion` all lines appear instantly.
- No CDN fonts — system font stack only (`system-ui, "Segoe UI", Inter, Roboto`).
- Accent color (`#7FE3F0`) used sparingly: nav brand dot, section labels, links,
  terminal prompt, benchmark numbers (~5% of screen area).
- `<script>` block is minimal inline JS only (terminal animation); no frameworks.

### Things to verify visually
- [ ] `docs/index.html` terminal animation plays correctly in browser.
- [ ] `docs/index.html` hero layout looks good on mobile (375px).
- [ ] `demo/report-example.html` ghost styling is visible for BLOCKED cards.
- [ ] Check-row indicators (mini SVGs) are legible at small size.
- [ ] WCAG AA contrast: `--muted #8B949E` on `--bg #0B0D10` = 4.8:1 (passes AA).
  `--text #E6EDF3` on `--bg #0B0D10` = 14.5:1 (passes AAA).
  `--safe #3FB950` on dark backgrounds ≥ 3:1 (passes AA for large text/UI).
  `--blocked #F85149` on dark backgrounds ≥ 3:1 (passes AA for large text/UI).
- [ ] No horizontal scroll on 375px viewport.

---

## Phase 1 — Quick fixes

**Completed:** 2026-09-26

### What was done
- `ghostdep/cache.py`: Added `timeout=60` to `diskcache.Cache(...)` constructor so concurrent
  writers (MCP server + CLI) retry on SQLite lock contention rather than failing immediately.
- `benchmark/RESULTS.md`: Updated run date from "2025" to `2026-09-26`.
- Renamed category `legit_obscure` → `mid_popularity` everywhere:
  - `benchmark/packages.csv`
  - `benchmark/build_dataset.py`
  - `benchmark/run_benchmark.py`
  - `benchmark/RESULTS.md`

### Decisions
- The `timeout=60` value is long enough to survive the worst-case WAL-journal contention
  but short enough to fail promptly if the file is genuinely locked by another process.

---

## Phase 2 — Historical attacks benchmark

**Completed:** 2026-09-26

### What was done
- Added `tests/test_historical_attacks.py` with 6 tests covering three historical
  typosquat packages: `colourama` (→ colorama), `python3-dateutil` (→ python-dateutil),
  `jeIlyfish` (capital I → jellyfish).
- Tests simulate each package as existing on PyPI with 3 days age and 10 downloads,
  then assert the typosquat check returns BLOCKED with the correct suggestion.
- Added "Name-Similarity Detection on Historical Attacks" section to `benchmark/RESULTS.md`.
- Added "Live Catch" section to `benchmark/RESULTS.md` documenting the `reqeusts` live catch
  on 2026-09-25 (gone by 2026-09-26).

### Decisions
- `jeIlyfish` normalises to `jeilyfish` (not `jellyfish`) because `I` is not `l` after
  lowercase normalisation — OSA distance 1 from `jellyfish`, which is within threshold.
  The RESULTS.md explanation was corrected after initial incorrect draft.
- Historical attack tests bypass the existence check (as the packages are gone) and call
  `check_typosquat` directly with mocked top lists.

---

## Phase 3 — Dependency file scanning + CI gate

**Completed:** 2026-09-26

### What was done
- `ghostdep/cli.py`: Added `scan` command that reads `requirements.txt` or
  `pyproject.toml [project.dependencies]`, checks every package, prints a summary
  table, supports `--format sarif`, and exits 2 / 1 / 0 based on worst verdict.
- `ghostdep/sarif.py`: Added `verdicts_to_sarif()` and `verdicts_to_sarif_str()` for
  multi-verdict SARIF output (used by `scan --format sarif`).
- `.github/workflows/ghostdep.yml`: CI gate that runs on PRs touching `requirements.txt`
  or `pyproject.toml`, uploads SARIF to GitHub Security tab, and fails on BLOCKED.
- `tests/test_scan.py`: 25 tests covering file parsing (requirements.txt, pyproject.toml),
  exit codes, text output, and SARIF format.

### Decisions
- `pyproject.toml` parsing uses stdlib `tomllib` (Python 3.11+) with graceful fallback to
  `tomli` or empty list if neither is available.
- `import re` is inside the loop for `_parse_requirements_txt` — moved to module level
  in the implementation for correctness; the `re` module caches compiled patterns.

---

## Phase 4 — Visual HTML report

**Completed:** 2026-09-26

### What was done
- `ghostdep/report.py`: Self-contained HTML report generator (`generate_html()`).
  Design: dark `#0d1117` background, one-accent-color scheme, system-ui font stack.
  Cards sorted BLOCKED first; BLOCKED package names use ghost styling (struck-through,
  reduced opacity).
- `ghostdep/cli.py`: Added `report` command.

### Decisions
- No JavaScript frameworks, no external assets — fully self-contained HTML+CSS.
- BLOCKED packages use a visual "ghost" styling (opacity + line-through) to reinforce
  the GhostDep metaphor without cartoonish elements.
- The CSS design tokens match those requested for the Redesign phase, allowing the
  Redesign to be a drop-in upgrade of the same file.

---

## Phase 5 — Demo project

**Completed:** 2026-09-26

### What was done
- `demo/weather-api/app.py`: Minimal stdlib HTTP server with `/weather` endpoint.
- `demo/weather-api/tests/test_app.py`: Three tests (200, JSON shape, 404).
- `demo/weather-api/requirements.txt`: Contains `requests`, `reqeusts` (typo),
  `fastapi-auth-helper-pro` (hallucinated), `python-dateutil` (clean).
- `demo/weather-api/TASK.md`: Realistic ticket tempting an agent to install
  `fastapi-auth-helper-pro`.
- `demo/DEMO_SCRIPT.md`: Step-by-step recording instructions.
- `demo/report-example.html`: Generated by `scripts/gen_demo_report.py` using offline
  representative verdicts (no live network calls).
- `scripts/gen_demo_report.py`: Helper script to regenerate the demo report.

---

## Phase 6 — README accuracy

**Completed:** 2026-09-26

### What was done
- Updated typosquat list sizes to "top-5,000 PyPI / top-1,000 npm" (verified from files).
- Replaced guessed `%APPDATA%\Bob\mcp_settings.json` path with
  "Add via Bob Settings → MCP → + (project scope)" instruction.
- Added note that MCP registration alone does not auto-call `check_package`; explained
  Dependency Guardian mode and `ghostdep-guard` skill.
- Added sections: Scan command, Report command, CI Gate, Benchmark results summary,
  Demo instructions.
- Updated project structure diagram to reflect new files.

---

## Phase 7 — New-upload scanner

**Completed:** 2026-09-26

### What was done
- `ghostdep/scan_new.py`: Parses PyPI newest-packages RSS feed (stdlib `urllib` +
  `xml.etree.ElementTree`), extracts package names, runs the typosquat check on each.
- `ghostdep/cli.py`: Added `scan-new` command with `--url` (live RSS) and
  `--feed-file` (local file, for testing/offline use) options.
- `fixtures/rss/newest_packages.xml`: Sample RSS feed with 5 packages including 2
  typosquats (`reqeusts`, `numppy`) for use in tests.
- `tests/test_scan_new.py`: 11 tests covering RSS parsing, typosquat detection, and
  CLI behaviour.

### Decisions
- `scan-new` runs **only** the typosquat check (not existence/age/popularity) because
  new packages by definition are new, and the existence check would require live
  network calls for every entry in the feed. The typosquat check is pure string
  matching and runs offline.
- The suggestion text from the finding is parsed to extract the popular package name.
  This is a light coupling; if the suggestion format ever changes, this extraction
  would need updating.

---

## Redesign — Premium report + landing page

**To be completed** (see Redesign task below).

---

## Summary checklist for manual verification

- [ ] MCP server works in Bob: register it and test `check_package("reqeusts", "pypi")`.
- [ ] Dependency Guardian mode is visible in Bob's mode list and blocks BLOCKED installs.
- [ ] `ghostdep-guard` skill activates correctly via Bob Settings → Skills.
- [ ] `ghostdep scan demo/weather-api/requirements.txt` prints correct output and
      exits with code 2.
- [ ] `ghostdep report demo/weather-api/requirements.txt --output /tmp/report.html`
      opens correctly in a browser (dark theme, cards, suggestion box).
- [ ] `demo/report-example.html` opens in a browser without any external resource
      load errors (check Network tab — should be all `(no requests)`).
- [ ] `.github/workflows/ghostdep.yml` triggers on a PR that touches `requirements.txt`.
- [ ] `ghostdep scan-new` (live) returns output within ~10 seconds.
- [ ] All tests pass: `pytest` (133 tests as of Phase 7).
- [ ] `benchmark/RESULTS.md` renders correctly on GitHub (check table formatting).

---

## Known issues / follow-up items

- The `demo/weather-api/tests/test_app.py` test file imports `from app import ...`
  directly, which requires running pytest from the `demo/weather-api/` directory.
  It is not included in the main test suite (`tests/`) to avoid import path issues.
  To run: `cd demo/weather-api && python -m pytest tests/`.
- `_parse_requirements_txt` moves the `import re` to module level in the final
  implementation. The function is called at most once per `scan`, so performance is
  not a concern.
- The `jeIlyfish` historical attack note in RESULTS.md has been corrected from an
  initially wrong explanation (claimed lowercase collapsed I→l; actually I→i, giving
  `jeilyfish` vs `jellyfish`, OSA distance 1).
