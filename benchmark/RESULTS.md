# GhostDep Benchmark Results

**Total packages tested:** 75  
**Date run:** 2026-09-26 (live PyPI registry, 1 s sleep between requests)
**Seed:** 42 (fully reproducible)

---

## Summary

| Metric | Value |
|---|---|
| Detection rate (typosquat + hallucinated) | **30/30 (100%)** |
| False-positive rate (popular + mid\_popularity) | **0/45 (0%)** |
| Errors | 0 |

---

## Per-Category Results

| Category | Expected | Total | Correct | Wrong | Errors |
|---|---|---|---|---|---|
| popular | SAFE | 30 | 30 | 0 | 0 |
| mid\_popularity | SAFE or SUSPICIOUS | 15 | 15 | 0 | 0 |
| typosquat | BLOCKED | 15 | 15 | 0 | 0 |
| hallucinated | BLOCKED | 15 | 15 | 0 | 0 |

---

## Mismatches

_No mismatches — all 75 verdicts matched expectations._

---

## Observations

### Detection mechanism for typosquats
All 15 generated typosquat names (`reqeusts`, `packagging`, `setptools`, etc.) were
caught by **Check 1 (existence)** — they do not exist on PyPI at all, so they return
404 → BLOCKED before the typosquat edit-distance check even runs.  
This is the correct and expected behaviour: an AI agent asking to install a
non-existent package is the highest-confidence signal of hallucination or
typosquatting.  The OSA edit-distance typosquat check (Check 4) acts as a second
line of defence for cases where the misspelled name **does** exist on PyPI (uploaded
by a real attacker).

### mid_popularity packages all came back SAFE
All 15 packages from ranks 3000–5000 (e.g. `hyperpyyaml`, `scalar-fastapi`,
`vercel-headers`) passed with SAFE, not SUSPICIOUS.  This indicates that even
moderately obscure packages tend to have enough historical downloads to clear the
popularity threshold (`PYPI_MIN_DOWNLOADS_MONTH = 1 000`) and are old enough to
clear the age check (`MIN_AGE_DAYS = 30`).  The SUSPICIOUS tier therefore mainly
fires for brand-new packages and very niche packages not covered by the top-5 000
list.

### Popular packages — zero false positives
All 30 packages sampled from the top-500 (e.g. `pygments`, `pillow`, `pyyaml`,
`litellm`) were correctly classified SAFE.  The popularity and age checks are
calibrated conservatively enough that well-established packages are not penalised.

---

## Known Bugs / Issues Found During Benchmark

### Diskcache SQLite contention on Windows
**Symptom:** `sqlite3.OperationalError: database or disk is full` when the benchmark
runner and the GhostDep MCP server process both try to open the same SQLite cache
file (`~/.cache/ghostdep/cache.db`) concurrently.

**Root cause:** diskcache uses SQLite WAL mode. When two processes open the same
WAL-journal database on Windows, the second writer receives SQLITE_FULL (misreported
as "disk full") rather than a proper locking error.

**Workaround applied in benchmark:** `run_benchmark.py` patches `CACHE_DIR` to a
separate path (`.cache/ghostdep-benchmark/`) before importing any ghostdep module,
so the benchmark and the MCP server never share a cache file.

**Recommended fix in ghostdep (not applied — per benchmark rules):** Open
`diskcache.Cache` with `timeout=60` so concurrent writers retry rather than fail
immediately, or use a per-process cache path derived from `os.getpid()`.

---

## All Results

| Package | Category | Expected | Verdict | Match | Reasons |
|---|---|---|---|---|---|
| `cbor2` | popular | SAFE | SAFE | yes | |
| `propcache` | popular | SAFE | SAFE | yes | |
| `pygments` | popular | SAFE | SAFE | yes | |
| `xlrd` | popular | SAFE | SAFE | yes | |
| `sortedcontainers` | popular | SAFE | SAFE | yes | |
| `exceptiongroup` | popular | SAFE | SAFE | yes | |
| `editables` | popular | SAFE | SAFE | yes | |
| `pillow` | popular | SAFE | SAFE | yes | |
| `onnxruntime` | popular | SAFE | SAFE | yes | |
| `yarl` | popular | SAFE | SAFE | yes | |
| `uc-micro-py` | popular | SAFE | SAFE | yes | |
| `caio` | popular | SAFE | SAFE | yes | |
| `azure-storage-blob` | popular | SAFE | SAFE | yes | |
| `pyjwt` | popular | SAFE | SAFE | yes | |
| `vcs-versioning` | popular | SAFE | SAFE | yes | |
| `blinker` | popular | SAFE | SAFE | yes | |
| `six` | popular | SAFE | SAFE | yes | |
| `python-dateutil` | popular | SAFE | SAFE | yes | |
| `litellm` | popular | SAFE | SAFE | yes | |
| `psutil` | popular | SAFE | SAFE | yes | |
| `openpyxl` | popular | SAFE | SAFE | yes | |
| `execnet` | popular | SAFE | SAFE | yes | |
| `google-cloud-kms` | popular | SAFE | SAFE | yes | |
| `pyyaml` | popular | SAFE | SAFE | yes | |
| `cython` | popular | SAFE | SAFE | yes | |
| `jiter` | popular | SAFE | SAFE | yes | |
| `text-unidecode` | popular | SAFE | SAFE | yes | |
| `linkify-it-py` | popular | SAFE | SAFE | yes | |
| `mccabe` | popular | SAFE | SAFE | yes | |
| `xxhash` | popular | SAFE | SAFE | yes | |
| `tensorflow-hub` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `looseversion` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `rioxarray` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `lief` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `nemo-toolkit` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `pyapns-client` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `macholib` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `lazrs` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `coola` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `python-lsp-server` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `ecos` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `sanic-routing` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `hyperpyyaml` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `vercel-headers` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `scalar-fastapi` | mid\_popularity | SAFE\_OR\_SUSPICIOUS | SAFE | yes | |
| `reqeusts` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `pycpparser` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `packagging` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `python-multipar` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `grpci` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `trov-eclassifiers` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `botocre` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `aiohappyeyebalsl` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `ppython-dotenv` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `tzzdata` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `refernecing` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `jonschema-specifications` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `charset-onrmalizer` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `setptools` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `referencinng` | typosquat | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `fastapi-auth-helper-pro` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `django-supermodel` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `pydantic-schema-validator-plus` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `requests-async-client` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `numpy-accelerate-gpu` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `sqlalchemy-smart-orm` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `flask-restplus-extended` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `torch-model-utils` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `pandas-ai-agent` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `langchain-vector-store-pro` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `cryptography-fips-adapter` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `pytest-ai-fixtures` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `click-rich-formatter` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `httpx-retry-middleware` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |
| `celery-task-scheduler-pro` | hallucinated | BLOCKED | BLOCKED | yes | existence:BLOCKED (404) |

---

## Notes

- `mid_popularity` packages (ranks 3000–5000) may legitimately be flagged SUSPICIOUS
  by the age or popularity checks; only a BLOCKED verdict counts as a false positive
  for that category.
- The typosquat check depends on OSA edit-distance against
  `ghostdep/data/top_pypi.txt`. Names generated by the benchmark may already exist on
  PyPI as legitimate packages — the existence check fires first in that case, so the
  package could be SAFE or SUSPICIOUS on its own merits rather than BLOCKED.
- API errors (network timeouts, rate-limiting) are recorded under match=error and
  counted in the Errors column, not as mismatches. None occurred in this run.
