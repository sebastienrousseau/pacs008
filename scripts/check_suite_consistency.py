#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Check the published pacs008 suite agrees with its own policy.

The suite ships one version number across every package. That is easy to
state and easy to let slip, because nothing breaks when it does: a
satellite left a release behind still installs, still imports, still
passes its own tests. It just quietly means something different from what
it says.

Two failures this catches, both of which had already happened here:

* **A member left behind.** `pacs008` was at 0.0.10 while `pacs008-mcp`
  carried 0.0.9 and `pacs008-loader-mt103` 0.0.3 — three different numbers
  for one suite.

* **A version bumped in the tree and never released.** Three repositories
  in the wider suite have done this, each time stranding a `cryptography`
  advisory floor that reached nobody. Nothing fails when it happens; only
  PyPI disagrees, and only if somebody looks. This looks.

Exits non-zero when the suite disagrees with itself, so a schedule turns
into a notification rather than a report nobody opens.

Usage:
    python3 scripts/check_suite_consistency.py
    python3 scripts/check_suite_consistency.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent

#: Every published member of the pacs008 suite. The core is first.
MEMBERS = (
    "pacs008",
    "pacs008-mcp",
    "pacs008-loader-mt103",
)

TIMEOUT = 30


def published_version(distribution: str) -> str | None:
    """The newest version of ``distribution`` on PyPI, or None."""
    url = f"https://pypi.org/pypi/{distribution}/json"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return str(json.load(response)["info"]["version"])
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return None


def tree_version() -> str:
    """The version this checkout declares."""
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    poetry = data.get("tool", {}).get("poetry", {})
    return str(poetry.get("version") or data["project"]["version"])


def check() -> tuple[list[str], dict[str, object]]:
    """Return (problems, report)."""
    problems: list[str] = []
    tree = tree_version()
    published = {name: published_version(name) for name in MEMBERS}

    core_published = published[MEMBERS[0]]

    # 1. The tree must not be ahead of what was released. A bump that was
    #    never tagged looks exactly like this and nothing else notices.
    if core_published and core_published != tree:
        problems.append(
            f"{MEMBERS[0]}: tree is {tree} but PyPI has {core_published}. "
            f"Either the release was never tagged, or the tree is behind."
        )

    # 2. Every member ships the core's number.
    for name, version in published.items():
        if version is None:
            problems.append(f"{name}: could not read PyPI")
        elif core_published and version != core_published:
            problems.append(
                f"{name}: published {version}, but the suite is at "
                f"{core_published}"
            )

    return problems, {
        "tree": tree,
        "published": published,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    problems, report = check()
    if args.json:
        json.dump(report, sys.stdout, indent=1)
        print()
    else:
        print(f"tree version: {report['tree']}")
        for name, version in report["published"].items():  # type: ignore[union-attr]
            print(f"  {name:26} {version}")
        if problems:
            print("\nproblems:")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print("\nthe suite agrees with itself")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
