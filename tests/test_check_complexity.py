# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""The complexity gate catches each ceiling, and its baseline only shrinks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def gate() -> ModuleType:
    """A fresh copy of the gate, so monkeypatched paths never leak."""
    spec = importlib.util.spec_from_file_location(
        "check_complexity", ROOT / "scripts" / "check_complexity.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _branchy() -> str:
    body = "".join(
        f"    if x == {i}:\n        return {i}\n" for i in range(11)
    )
    return f"def branchy(x):\n{body}    return -1\n"


def _nested() -> str:
    # Cognitive complexity charges each level of nesting again: five nested
    # loops and conditions cost 1 + 2 + 3 + 4 + 5 = 15, exactly the
    # ceiling, so a sixth level is what goes over it.
    return (
        "def nested(rows):\n"
        "    for a in rows:\n"
        "        for b in a:\n"
        "            for c in b:\n"
        "                for d in c:\n"
        "                    for e in d:\n"
        "                        if e:\n"
        "                            return e\n"
        "    return None\n"
    )


def _long() -> str:
    body = "".join(f"    y{i} = {i}\n" for i in range(60))
    return f"def long():\n{body}    return 0\n"


def _difficult() -> str:
    # Halstead difficulty is (distinct operators / 2) * (operands /
    # distinct operands): one operand under twelve operators.
    ops = ["+", "-", "*", "/", "//", "%", "**", "<<", ">>", "&", "|", "^"]
    body = "".join(f"    c = c {op} c\n" for op in ops * 2)
    return f"def difficult(c):\n{body}    return c\n"


@pytest.mark.parametrize(
    ("source", "key", "metric"),
    [
        (_branchy(), "offender.py::branchy", "cyclomatic"),
        (_nested(), "offender.py::nested", "cognitive"),
        (_long(), "offender.py::long", "lines"),
        (_difficult(), "offender.py::difficult", "halstead"),
        ("x = 1\n" * 501, "offender.py", "file_lines"),
    ],
    ids=["cyclomatic", "cognitive", "function-lines", "halstead", "file"],
)
def test_each_ceiling_is_caught(
    gate: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    key: str,
    metric: str,
) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    path = tmp_path / "offender.py"
    path.write_text(source, encoding="utf-8")
    report = gate.measure_file(path)
    assert metric in report.get(key, {}), report


def test_a_function_within_every_ceiling_is_not_reported(
    gate: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    path = tmp_path / "fine.py"
    path.write_text("def fine(x):\n    return x + 1\n", encoding="utf-8")
    assert gate.measure_file(path) == {}


def test_a_new_offender_fails(gate: ModuleType) -> None:
    problems = gate.compare({"a.py::f": {"cyclomatic": 11}}, {})
    assert problems == ["a.py::f: cyclomatic 11 is over the ceiling"]


def test_a_baselined_offender_may_not_get_worse(gate: ModuleType) -> None:
    baseline = {"a.py::f": {"lines": 70}}
    problems = gate.compare({"a.py::f": {"lines": 75}}, baseline)
    assert problems == ["a.py::f: lines rose from 70 to 75"]


def test_an_improvement_must_shrink_the_baseline(gate: ModuleType) -> None:
    baseline = {"a.py::f": {"lines": 70}}
    problems = gate.compare({}, baseline)
    assert problems == [
        "a.py::f: lines improved from 70 to within the ceiling; "
        "run with --update to shrink the baseline"
    ]


def test_an_unchanged_offender_passes(gate: ModuleType) -> None:
    baseline = {"a.py::f": {"lines": 70}}
    assert gate.compare({"a.py::f": {"lines": 70}}, baseline) == []


def test_the_tree_matches_its_baseline(
    gate: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gate.main([]) == 0
    assert "none worse" in capsys.readouterr().out


def test_update_rewrites_the_baseline(
    gate: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = tmp_path / "complexity-baseline.json"
    monkeypatch.setattr(gate, "BASELINE", baseline)
    assert gate.main(["--update"]) == 0
    assert json.loads(baseline.read_text(encoding="utf-8")) == gate.measure()


def test_an_offender_fails_the_run(
    gate: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "bad.py").write_text(_branchy(), encoding="utf-8")
    (tmp_path / "complexity-baseline.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "PATHS", ("pkg",))
    monkeypatch.setattr(
        gate, "BASELINE", tmp_path / "complexity-baseline.json"
    )
    assert gate.main([]) == 1
    assert "pkg/bad.py::branchy: cyclomatic" in capsys.readouterr().err
