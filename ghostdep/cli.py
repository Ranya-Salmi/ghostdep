"""GhostDep CLI — stub (full implementation in step 10)."""
import click


@click.group()
def main() -> None:
    """GhostDep — security guard for AI coding agents."""


@main.command()
@click.argument("name")
@click.option("--ecosystem", default="pypi", type=click.Choice(["pypi", "npm"]))
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "sarif"]))
@click.option("--offline", is_flag=True)
def check(name: str, ecosystem: str, fmt: str, offline: bool) -> None:
    """Check a package for security issues."""
    import os
    if offline:
        os.environ["GHOSTDEP_OFFLINE"] = "1"
    from ghostdep.checker import run_checks
    verdict = run_checks(name, ecosystem)
    click.echo(f"{verdict.overall.value}: {name} ({ecosystem})")
    for f in verdict.findings:
        click.echo(f"  [{f.severity.value}] {f.check}: {f.message}")
        if f.suggestion:
            click.echo(f"    -> {f.suggestion}")
