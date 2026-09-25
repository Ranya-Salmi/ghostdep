"""GhostDep CLI — `ghostdep check <name> [OPTIONS]`."""
from __future__ import annotations

import os
import sys

import click

from ghostdep.checker import run_checks
from ghostdep.verdict import Severity


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
