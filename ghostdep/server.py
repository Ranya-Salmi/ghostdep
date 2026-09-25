"""GhostDep MCP server — exposes check_package as an MCP tool over stdio."""
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP

from ghostdep.checker import run_checks

mcp = FastMCP("ghostdep")


@mcp.tool()
async def check_package(name: str, ecosystem: str) -> dict:
    """
    Check a package for hallucination, typosquatting, age, popularity,
    and known vulnerabilities.

    Args:
        name: Package name, e.g. "requests"
        ecosystem: "pypi" or "npm"

    Returns:
        Verdict dict with overall (SAFE/SUSPICIOUS/BLOCKED), findings list,
        and optional suggestion.
    """
    verdict = await asyncio.to_thread(run_checks, name, ecosystem)
    return verdict.to_dict()


if __name__ == "__main__":
    mcp.run(transport="stdio")
