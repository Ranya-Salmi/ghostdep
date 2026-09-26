"""GhostDep MCP server — exposes check_package as an MCP tool over stdio."""
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP

from ghostdep.checker import run_checks
from ghostdep.policy import load_policy

mcp = FastMCP("ghostdep")


@mcp.tool()
async def check_package(name: str, ecosystem: str) -> dict:
    """
    Check a package for hallucination, typosquatting, age, popularity,
    and known vulnerabilities. Call this BEFORE adding any package to a
    dependency file or running an install command. Never install a package
    whose overall verdict is BLOCKED; ask the user about SUSPICIOUS ones.

    Args:
        name: Package name, e.g. "requests"
        ecosystem: "pypi" or "npm"

    Returns:
        Verdict dict with overall (SAFE/SUSPICIOUS/BLOCKED), findings list,
        and optional suggestion.
    """
    verdict = await asyncio.to_thread(_check, name, ecosystem)
    return verdict.to_dict()


def _check(name: str, ecosystem: str):
    """Apply the team policy (.ghostdep.toml) first, then run the checks."""
    decided = load_policy().verdict_for(name, ecosystem)
    return decided if decided is not None else run_checks(name, ecosystem)


if __name__ == "__main__":
    mcp.run(transport="stdio")
