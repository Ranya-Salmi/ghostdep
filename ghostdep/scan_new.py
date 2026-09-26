"""New-upload scanner: reads PyPI newest-packages RSS and checks for typosquats.

Used by `ghostdep scan-new`.
"""
from __future__ import annotations

import urllib.request
import urllib.error
from xml.etree import ElementTree

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


def check_new_packages(
    names: list[str],
    ecosystem: str = "pypi",
) -> list[tuple[str, str]]:
    """Check each *name* against the typosquat list only (no network).

    Returns a list of (name, closest_popular) tuples for packages that look
    like typosquats.  Uses the typosquat check directly with dummy age/download
    values so only the name-similarity logic runs.
    """
    from datetime import datetime, timedelta, timezone

    from ghostdep.checks.typosquat import check_typosquat

    # Simulate: package exists, uploaded today, 0 downloads
    first_release = datetime.now(tz=timezone.utc) - timedelta(days=1)
    download_count = 0

    lookalikes: list[tuple[str, str]] = []
    for name in names:
        finding = check_typosquat(name, ecosystem, download_count, first_release)
        if finding is not None and finding.suggestion:
            # Extract the popular name from suggestion "Did you mean 'X'?"
            suggestion = finding.suggestion
            # suggestion is "Did you mean 'popular_name'?"
            popular = suggestion.replace("Did you mean '", "").rstrip("'?")
            lookalikes.append((name, popular))
    return lookalikes
