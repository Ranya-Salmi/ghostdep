"""Tests for Phase 7 — scan-new command and scan_new module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ghostdep.cli import main
from ghostdep.scan_new import parse_rss, check_new_packages


_FIXTURE_RSS = Path(__file__).parent.parent / "fixtures" / "rss" / "newest_packages.xml"

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PyPI newest packages</title>
    <item>
      <title>reqeusts 1.0.0</title>
      <link>https://pypi.org/project/reqeusts/</link>
    </item>
    <item>
      <title>legitimate-tool 0.1.0</title>
      <link>https://pypi.org/project/legitimate-tool/</link>
    </item>
  </channel>
</rss>"""

_CLEAN_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PyPI newest packages</title>
    <item>
      <title>my-brand-new-unique-helper 1.0.0</title>
    </item>
  </channel>
</rss>"""

_EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PyPI newest packages</title>
  </channel>
</rss>"""


# ---------------------------------------------------------------------------
# parse_rss unit tests
# ---------------------------------------------------------------------------

def test_parse_rss_extracts_names():
    names = parse_rss(_SAMPLE_RSS)
    assert "reqeusts" in names
    assert "legitimate-tool" in names


def test_parse_rss_strips_version():
    names = parse_rss(_SAMPLE_RSS)
    for name in names:
        assert " " not in name, f"Name contains space: {name!r}"


def test_parse_rss_empty_channel():
    names = parse_rss(_EMPTY_RSS)
    assert names == []


def test_parse_rss_fixture_file():
    """Validate the saved fixture file parses correctly."""
    xml_text = _FIXTURE_RSS.read_text(encoding="utf-8")
    names = parse_rss(xml_text)
    assert len(names) >= 3
    assert "reqeusts" in names
    assert "numppy" in names


# ---------------------------------------------------------------------------
# check_new_packages unit tests
# ---------------------------------------------------------------------------

def test_check_new_packages_detects_reqeusts():
    """reqeusts should be flagged as resembling requests."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["reqeusts"])
    assert len(lookalikes) == 1
    name, popular = lookalikes[0]
    assert name == "reqeusts"
    assert "requests" in popular


def test_check_new_packages_clean_name_not_flagged():
    """A totally unique name should not be flagged."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests", "flask"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["completely-unique-tool-xyz123"])
    assert lookalikes == []


def test_check_new_packages_multiple():
    """Multiple typosquats in the same feed."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests", "flask"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["reqeusts", "flaks"])
    names_found = [n for n, _ in lookalikes]
    assert "reqeusts" in names_found
    assert "flaks" in names_found


def test_check_new_packages_returns_list_of_tuples():
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
    ):
        result = check_new_packages(["reqeusts"])
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in result)


# ---------------------------------------------------------------------------
# scan-new CLI command tests
# ---------------------------------------------------------------------------

def test_scan_new_with_fixture_file_finds_lookalikes():
    """CLI --feed-file with the sample fixture should find reqeusts and numppy."""
    runner = CliRunner()
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests", "numpy", "flask"] if eco == "pypi" else [],
    ):
        result = runner.invoke(main, ["scan-new", "--feed-file", str(_FIXTURE_RSS)])
    assert result.exit_code == 0
    assert "reqeusts" in result.output or "numppy" in result.output


def test_scan_new_with_clean_feed_reports_none():
    """A feed with no typosquats should report 'no typosquats detected'."""
    runner = CliRunner()
    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(_CLEAN_RSS)
        tmp = f.name
    try:
        with patch(
            "ghostdep.checks.typosquat._load_top_list",
            side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
        ):
            result = runner.invoke(main, ["scan-new", "--feed-file", tmp])
        assert result.exit_code == 0
        assert "no typosquats" in result.output.lower()
    finally:
        os.unlink(tmp)


def test_scan_new_empty_feed():
    """An empty feed should not crash."""
    runner = CliRunner()
    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(_EMPTY_RSS)
        tmp = f.name
    try:
        result = runner.invoke(main, ["scan-new", "--feed-file", tmp])
        assert result.exit_code == 0
        assert "No packages" in result.output
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# Radar precision tests
# ---------------------------------------------------------------------------

def test_short_name_fdu_not_flagged():
    """Names shorter than RADAR_MIN_NAME_LENGTH (normalised) must be skipped."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests", "numpy", "flask"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["fdu"])
    assert lookalikes == [], "Short name 'fdu' (3 chars) should not be flagged"


def test_reqeusts_still_detected():
    """'reqeusts' (7 chars) must still be detected after radar precision changes."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["reqeusts"])
    names = [n for n, _ in lookalikes]
    assert "reqeusts" in names


def test_numppy_still_detected():
    """'numppy' must still be detected as a lookalike of 'numpy'."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["numpy"] if eco == "pypi" else [],
    ):
        lookalikes = check_new_packages(["numppy"])
    names = [n for n, _ in lookalikes]
    assert "numppy" in names


def test_name_in_top_list_not_flagged():
    """A name already in the top list (the real package) must be skipped."""
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests", "numpy"] if eco == "pypi" else [],
    ):
        # "requests" is in the top list — it must not be flagged as its own lookalike
        lookalikes = check_new_packages(["requests"])
    assert lookalikes == [], "'requests' is in the top list and must not be flagged"


def test_scan_new_output_heading():
    """scan-new output must say 'possible lookalike(s)' not 'potential typosquat(s)'."""
    runner = CliRunner()
    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(_SAMPLE_RSS)
        tmp = f.name
    try:
        with patch(
            "ghostdep.checks.typosquat._load_top_list",
            side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
        ):
            result = runner.invoke(main, ["scan-new", "--feed-file", tmp])
        assert "possible lookalike" in result.output.lower(), (
            f"Expected 'possible lookalike' in output, got: {result.output!r}"
        )
        assert "Lookalikes are not necessarily malicious" in result.output
    finally:
        os.unlink(tmp)

