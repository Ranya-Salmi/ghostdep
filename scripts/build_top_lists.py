"""scripts/build_top_lists.py

Downloads ranked package-name lists from real public datasets and writes:
  ghostdep/data/top_pypi.txt  — top N PyPI packages by download count
  ghostdep/data/top_npm.txt   — top npm packages by dependents count

PyPI source
-----------
Hugo van Kemenade's "top-pypi-packages" dataset:
  https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json

Updated monthly; lists up to 15 000 PyPI packages ranked by 30-day downloads.
This is the canonical source used by pip-audit, safety, and similar tools.

npm source
----------
Anvaka's npmrank gist (01.most-dependent-upon.md):
  https://gist.githubusercontent.com/anvaka/8e8fa57c7ee1350e3491/raw/01.most-dependent-upon.md

This dataset contains the top 1 000 most-depended-upon npm packages, ranked by
number of direct dependents.  There is no freely available public API or dataset
that provides a ranked download-count list of all npm packages; the npm
download-counts API requires a specific package name.  1 000 entries is
sufficient to catch the overwhelming majority of typosquatting targets
(lodash, chalk, react, express, webpack, etc.).  See README for details.

Usage
-----
    python scripts/build_top_lists.py [--size 5000]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx", file=sys.stderr)
    sys.exit(1)

PYPI_URL = (
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"
)
NPM_URL = (
    "https://gist.githubusercontent.com/anvaka/8e8fa57c7ee1350e3491"
    "/raw/01.most-dependent-upon.md"
)

DATA_DIR = Path(__file__).parent.parent / "ghostdep" / "data"


def fetch_top_pypi(size: int) -> list[str]:
    print(f"Fetching top PyPI packages from {PYPI_URL} …", flush=True)
    resp = httpx.get(PYPI_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("rows", [])
    names = [r["project"] for r in rows if r.get("project")]
    kept = names[:size]
    print(f"  Got {len(names)} packages; keeping top {len(kept)}.")
    return kept


def fetch_top_npm(size: int) -> list[str]:
    """Parse anvaka's most-dependent-upon markdown list.

    Lines look like:  0. [lodash](https://www.npmjs.org/package/lodash) - 69147
    The list contains exactly 1 000 entries.  size is capped at 1 000.
    """
    print(f"Fetching top npm packages from anvaka/npmrank …", flush=True)
    resp = httpx.get(NPM_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    # Match:  <digits>. [<name>](...)
    names = re.findall(r"^\d+\.\s+\[([^\]]+)\]", resp.text, re.MULTILINE)
    kept = names[:size]
    print(f"  Got {len(names)} packages; keeping top {len(kept)}.")
    if size > len(names):
        print(
            f"  NOTE: Only {len(names)} npm entries are available from this source "
            f"(requested {size}).  See README for details."
        )
    return kept


def write_list(path: Path, names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"  Wrote {len(names)} entries to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build top-package lists for GhostDep.")
    parser.add_argument(
        "--size",
        type=int,
        default=5000,
        help="Max packages per ecosystem (default: 5000; npm capped at 1000).",
    )
    args = parser.parse_args()

    pypi_names = fetch_top_pypi(args.size)
    write_list(DATA_DIR / "top_pypi.txt", pypi_names)

    npm_names = fetch_top_npm(args.size)
    write_list(DATA_DIR / "top_npm.txt", npm_names)

    print("Done.")


if __name__ == "__main__":
    main()
