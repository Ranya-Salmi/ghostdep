# ---------------------------------------------------------------------------
# All tunable thresholds live here as named constants.
# ---------------------------------------------------------------------------

# --- Age check -------------------------------------------------------------
MIN_AGE_DAYS: int = 30  # flag packages first released fewer than N days ago

# --- Popularity check — PyPI -----------------------------------------------
PYPI_MIN_DOWNLOADS_MONTH: int = 1_000  # monthly downloads via pypistats

# --- Popularity check — npm ------------------------------------------------
NPM_MIN_DOWNLOADS_WEEK: int = 500  # weekly downloads via npm download-counts API

# --- Typosquatting ---------------------------------------------------------
# Distance thresholds are dynamic (see checks/typosquat.py):
#   <= 5 chars -> max distance 1
#   >  5 chars -> max distance 2
TOP_LIST_SIZE: int = 5_000  # entries loaded from top_*.txt

# --- Caching ---------------------------------------------------------------
CACHE_DIR: str = "~/.cache/ghostdep"
CACHE_TTL_SECONDS: int = 3_600  # 1 hour

# --- External APIs ---------------------------------------------------------
PYPI_JSON_URL: str = "https://pypi.org/pypi/{name}/json"
NPM_REGISTRY_URL: str = "https://registry.npmjs.org/{name}"
PYPISTATS_RECENT_URL: str = "https://pypistats.org/api/packages/{name}/recent"
NPM_DOWNLOADS_URL: str = "https://api.npmjs.org/downloads/point/last-week/{name}"
OSV_API_URL: str = "https://api.osv.dev/v1/query"
