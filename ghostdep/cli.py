"""GhostDep CLI — `ghostdep check <name> [OPTIONS]` and `ghostdep scan <file>`."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import click

from ghostdep.checker import run_checks
from ghostdep.verdict import Severity, Verdict


_COLOUR = {
    Severity.SAFE: "green",
    Severity.SUSPICIOUS: "yellow",
    Severity.BLOCKED: "red",
}


def _print_text(verdict) -> None:
    """Print a human-readable, colour-highlighted report."""
    colour = _COLOUR[verdict.overall]
    click.echo(
        click.style(
            f"● {verdict.overall.value}: {verdict.package} ({verdict.ecosystem})",
            fg=colour,
            bold=True,
        )
    )
    if not verdict.findings:
        click.echo(click.style("  No issues found.", fg="green"))
        return
    for f in verdict.findings:
        bullet_colour = _COLOUR[f.severity]
        click.echo(
            click.style(f"  [{f.severity.value}]", fg=bullet_colour, bold=True)
            + f" {f.check}: {f.message}"
        )
        if f.suggestion:
            click.echo(f"    → {f.suggestion}")


def _print_sarif(verdict) -> None:
    """Print SARIF 2.1.0 JSON to stdout."""
    from ghostdep.sarif import verdict_to_sarif_str
    click.echo(verdict_to_sarif_str(verdict))


@click.group()
def main() -> None:
    """GhostDep — security guard for AI coding agents."""


@main.command()
@click.argument("name")
@click.option(
    "--ecosystem",
    default="pypi",
    show_default=True,
    type=click.Choice(["pypi", "npm"]),
    help="Package ecosystem.",
)
@click.option(
    "--format",
    "fmt",
    default="text",
    show_default=True,
    type=click.Choice(["text", "sarif"]),
    help="Output format.",
)
@click.option(
    "--offline",
    is_flag=True,
    help="Run in offline mode (uses cached fixtures, no network calls).",
)
def check(name: str, ecosystem: str, fmt: str, offline: bool) -> None:
    """Check a package for security issues."""
    if offline:
        os.environ["GHOSTDEP_OFFLINE"] = "1"

    verdict = run_checks(name, ecosystem)

    if fmt == "sarif":
        _print_sarif(verdict)
    else:
        _print_text(verdict)

    # Exit with non-zero code when something is wrong so CI pipelines can act on it
    if verdict.overall == Severity.BLOCKED:
        sys.exit(2)
    elif verdict.overall == Severity.SUSPICIOUS:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Dependency file parsing helpers
# ---------------------------------------------------------------------------

def _parse_requirements_txt(path: Path) -> list[str]:
    """Return package names from a requirements.txt file.

    Handles:
    - Blank lines and comment lines (# …)
    - Version specifiers: requests>=2.0, requests==2.28.0, requests~=2.0, etc.
    - Extras: requests[security]
    - Editable installs (-e …) → skipped
    - Option lines (-r, --index-url, etc.) → skipped
    """
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            continue  # options / editable installs
        # Strip inline comments
        line = line.split("#")[0].strip()
        if not line:
            continue
        # Strip extras [...]
        import re
        name = re.split(r"[\[;,<>=!~\s]", line)[0].strip()
        if name:
            names.append(name)
    return names


def _parse_pyproject_toml(path: Path) -> list[str]:
    """Return package names from [project.dependencies] in pyproject.toml.

    Uses the stdlib tomllib (Python 3.11+) or tomli fallback.
    Returns an empty list if the section is absent or parsing fails.
    """
    try:
        try:
            import tomllib  # type: ignore[import]
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[import]
            except ImportError:
                return []
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        import re
        names: list[str] = []
        for dep in deps:
            name = re.split(r"[\[;,<>=!~\s]", dep.strip())[0].strip()
            if name:
                names.append(name)
        return names
    except Exception:
        return []


def _read_packages(file_path: Path) -> list[str]:
    """Dispatch to the appropriate parser based on file name."""
    name = file_path.name.lower()
    if name == "requirements.txt":
        return _parse_requirements_txt(file_path)
    if name == "pyproject.toml":
        return _parse_pyproject_toml(file_path)
    # Unknown file: attempt requirements.txt format
    return _parse_requirements_txt(file_path)


# ---------------------------------------------------------------------------
# Scan command
# ---------------------------------------------------------------------------

def _print_scan_summary(verdicts: list[Verdict], fmt: str) -> None:
    """Print the summary table (text format) or SARIF JSON."""
    if fmt == "sarif":
        from ghostdep.sarif import verdicts_to_sarif_str
        click.echo(verdicts_to_sarif_str(verdicts))
        return

    # Counts
    counts = {Severity.SAFE: 0, Severity.SUSPICIOUS: 0, Severity.BLOCKED: 0}
    for v in verdicts:
        counts[v.overall] += 1

    total = len(verdicts)
    click.echo("")
    click.echo(click.style("GhostDep Scan Summary", bold=True))
    click.echo(f"  {'Package':<35} {'Verdict':<12} {'Reasons'}")
    click.echo("  " + "─" * 70)
    for v in verdicts:
        colour = _COLOUR[v.overall]
        reasons = "; ".join(f.message[:50] for f in v.findings) if v.findings else ""
        suggestion = next((f.suggestion for f in v.findings if f.suggestion), "")
        verdict_label = click.style(f"{v.overall.value:<12}", fg=colour, bold=True)
        click.echo(f"  {v.package:<35} {verdict_label} {reasons}")
        if suggestion:
            click.echo(f"  {'':35}   → {suggestion}")
    click.echo("  " + "─" * 70)
    safe_s = click.style(f"{counts[Severity.SAFE]} SAFE", fg="green")
    susp_s = click.style(f"{counts[Severity.SUSPICIOUS]} SUSPICIOUS", fg="yellow")
    blk_s = click.style(f"{counts[Severity.BLOCKED]} BLOCKED", fg="red")
    click.echo(f"  {total} packages checked: {safe_s}  {susp_s}  {blk_s}")
    click.echo("")


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--ecosystem",
    default="pypi",
    show_default=True,
    type=click.Choice(["pypi", "npm"]),
    help="Package ecosystem.",
)
@click.option(
    "--format",
    "fmt",
    default="text",
    show_default=True,
    type=click.Choice(["text", "sarif"]),
    help="Output format.",
)
def scan(file: Path, ecosystem: str, fmt: str) -> None:
    """Scan a dependency file (requirements.txt / pyproject.toml) for risky packages.

    Exits 2 if any package is BLOCKED, 1 if any are SUSPICIOUS, 0 if all SAFE.
    """
    packages = _read_packages(file)
    if not packages:
        click.echo(f"No packages found in {file}.", err=True)
        sys.exit(0)

    verdicts: list[Verdict] = []
    for name in packages:
        v = run_checks(name, ecosystem)
        verdicts.append(v)

    _print_scan_summary(verdicts, fmt)

    # Determine exit code from worst verdict
    worst = Severity.SAFE
    for v in verdicts:
        if v.overall == Severity.BLOCKED:
            worst = Severity.BLOCKED
            break
        if v.overall == Severity.SUSPICIOUS:
            worst = Severity.SUSPICIOUS

    if worst == Severity.BLOCKED:
        sys.exit(2)
    elif worst == Severity.SUSPICIOUS:
        sys.exit(1)
