#!/usr/bin/env python3
"""Generate the regression coverage matrix.

Walks every module under ``pacs008/`` (excluding bundled templates,
schemas, tmp output and __pycache__), parses each file's AST, and
emits a Markdown table mapping each public top-level symbol to the
test files that reference it.

A "reference" is considered present if either:

1. The symbol identifier appears as a whole word in the test file's
   source (the common case), OR
2. The test file imports the module that defines the symbol (which
   catches API route handlers tested via FastAPI TestClient + pydantic
   models referenced as response types, where the symbol name itself
   may never appear).

Run from the repo root::

    poetry run python scripts/regression_matrix.py > docs/REGRESSION_MATRIX.md
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path("pacs008")
TESTS = pathlib.Path("tests")
EXCLUDE_DIRS = {"templates", "schemas", "tmp", "__pycache__"}


def public_symbols(py_file: pathlib.Path):
    """Yield ``(name, lineno)`` for top-level public classes/functions."""
    tree = ast.parse(py_file.read_text())
    for node in tree.body:
        name = getattr(node, "name", None)
        if not name or name.startswith("_"):
            continue
        if isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            yield name, node.lineno


def module_dotted(py_file: pathlib.Path) -> str:
    """Convert ``pacs008/foo/bar.py`` to ``pacs008.foo.bar``."""
    parts = list(py_file.with_suffix("").parts)
    return ".".join(parts)


def main() -> int:
    test_texts = {p: p.read_text() for p in TESTS.rglob("test_*.py")}

    def tests_referencing(symbol: str, module: str) -> list[str]:
        sym_pat = re.compile(rf"\b{re.escape(symbol)}\b")
        mod_pat = re.compile(
            rf"(?:from\s+{re.escape(module)}|import\s+{re.escape(module)})"
        )
        out = []
        for p, text in test_texts.items():
            if sym_pat.search(text) or mod_pat.search(text):
                out.append(p.name)
        return sorted(out)

    modules: dict[str, list] = defaultdict(list)
    for py_file in sorted(ROOT.rglob("*.py")):
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            continue
        rel = py_file.relative_to(ROOT.parent)
        dotted = module_dotted(py_file)
        for sym, lineno in public_symbols(py_file):
            refs = tests_referencing(sym, dotted)
            modules[str(rel)].append((sym, lineno, refs))

    # Render Markdown
    print("# Regression coverage matrix\n")
    print(
        "Generated from AST inspection of `pacs008/` and grep against\n"
        "`tests/test_*.py`. Each row maps a public top-level symbol\n"
        "(class, function, or coroutine) to test files that reference\n"
        "it **either** by identifier **or** by importing the module\n"
        "that defines it. The second condition catches FastAPI route\n"
        "handlers tested via `TestClient` calls and pydantic models\n"
        "used only as response types — where the symbol name does not\n"
        "appear in test source.\n"
    )
    print("**Regeneration command:**\n")
    print("```bash")
    print(
        "poetry run python scripts/regression_matrix.py "
        "> docs/REGRESSION_MATRIX.md"
    )
    print("```\n")

    covered = total = 0
    gaps: list[str] = []
    for mod, syms in sorted(modules.items()):
        if not syms:
            continue
        print(f"## `{mod}`\n")
        print("| Symbol | Line | Test files |")
        print("|---|---|---|")
        for name, lineno, refs in sorted(syms):
            total += 1
            if refs:
                covered += 1
                ref_md = ", ".join(f"`{r}`" for r in refs[:6])
                if len(refs) > 6:
                    ref_md += f" _(+{len(refs) - 6} more)_"
            else:
                ref_md = "**— no test reference —**"
                gaps.append(f"`{mod}::{name}`")
            print(f"| `{name}` | {lineno} | {ref_md} |")
        print()

    print("\n## Summary\n")
    print(f"- **Public top-level symbols inspected:** {total}")
    pct = covered * 100 // total if total else 0
    print(
        f"- **Referenced by ≥1 test file:** {covered} ({pct}%)"
    )
    print(f"- **Without test reference:** {len(gaps)}")
    if gaps:
        print("\n### Symbols with no test reference\n")
        for g in gaps:
            print(f"- {g}")
    else:
        print(
            "\n✅ Every public top-level symbol is referenced by ≥1 test file."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
