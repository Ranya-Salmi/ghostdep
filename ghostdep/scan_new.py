"""New-upload scanner: reads PyPI newest-packages RSS and checks for typosquats.

Used by `ghostdep scan-new`.

Radar precision rules (applied before the typosquat check):
- Skip names shorter than RADAR_MIN_NAME_LENGTH characters (normalised).
- Compare only against the top RADAR_TOP_N packages (not the full 5,000).
- Skip a name if it is already in the top list (it's the real package).
"""
from __future__ import annotations

import urllib.request
import urllib.error
from xml.etree import ElementTree

from ghostdep.constants import RADAR_MIN_NAME_LENGTH, RADAR_TOP_N

PYPI_RSS_URL = "https://pypi.org/rss/packages.xml"


def _fetch_rss(url: str = PYPI_RSS_URL, timeout: int = 10) -> str:
    """Fetch RSS XML from *url* and return as a string."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_rss(xml_text: str) -> list[str]:
    """Return package names from an RSS feed XML string.

    Parses <item><title>NAME VERSION</title>… entries.
    The name is everything before the first space in the title.
    """
    root = ElementTree.fromstring(xml_text)
    names: list[str] = []
    # RSS: /rss/channel/item/title
    for item in root.findall(".//item"):
        title_el = item.find("title")
        if title_el is None or not title_el.text:
            continue
        # Title format: "package-name 1.2.3"
        name = title_el.text.strip().split()[0]
        if name:
            names.append(name)
    return names


def _normalise(name: str) -> str:
    """Lowercase and strip separators — same transform as the typosquat check."""
    return name.lower().replace("-", "").replace("_", "").replace(".", "")


def check_new_packages(
    names: list[str],
    ecosystem: str = "pypi",
) -> list[tuple[str, str]]:
    """Check each *name* against the typosquat list only (no network).

    Returns a list of (name, closest_popular) tuples for packages that look
    like typosquats.  Uses the typosquat check directly with dummy age/download
    values so only the name-similarity logic runs.

    Radar precision filters applied before the check:
    - Skip names whose normalised form is shorter than RADAR_MIN_NAME_LENGTH.
    - Compare only against the top RADAR_TOP_N of the top list.
    - Skip a name if it already appears in the top list (it's the real package).
    """
    from datetime import datetime, timedelta, timezone

    from ghostdep.checks.typosquat import _load_top_list, check_typosquat

    # Simulate: package exists, uploaded today, 0 downloads
    first_release = datetime.now(tz=timezone.utc) - timedelta(days=1)
    download_count = 0

    # Build the radar-scoped top list once (top RADAR_TOP_N entries only)
    full_top = _load_top_list(ecosystem)
    radar_top_set = set(_normalise(n) for n in full_top[:RADAR_TOP_N])

    lookalikes: list[tuple[str, str]] = []
    for name in names:
        norm = _normalise(name)
        # Skip very short names (too many false positives)
        if len(norm) < RADAR_MIN_NAME_LENGTH:
            continue
        # Skip if this name is itself in the top-N (it's the real popular package)
        if norm in radar_top_set:
            continue
        finding = check_typosquat(name, ecosystem, download_count, first_release)
        if finding is not None and finding.suggestion:
            # Extract the popular name from suggestion "Did you mean 'X'?"
            suggestion = finding.suggestion
            # suggestion is "Did you mean 'popular_name'?"
            popular = suggestion.replace("Did you mean '", "").rstrip("'?")
            # Only report if the matched popular package is in the radar top-N
            if _normalise(popular) in radar_top_set:
                lookalikes.append((name, popular))
    return lookalikes
