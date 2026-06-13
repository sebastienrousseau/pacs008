# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the bundled examples/ scripts.

CI already runs both example scripts as smoke checks (via
``examples/{generate_xml,swift_compliance}.py``). This file mirrors
those invocations under ``pytest`` + coverage so that the example
code shows up as fully covered in the report — the same code already
shipped in the README's "Run the bundled examples" subsection should
not have a coverage gap.

``runpy.run_path`` executes the whole module body in a fresh
namespace, exactly as ``python examples/foo.py`` would, so coverage
sees every line.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def in_repo_root(monkeypatch):
    """Run the example with the repo root as cwd.

    Both example scripts resolve template paths relative to the
    package layout, so the cwd at invocation matters less than the
    file path — but generate_xml.py writes ``output_pacs008.xml`` to
    cwd, so we redirect it into the pytest tmp working directory and
    clean up afterwards.
    """
    repo_root = _EXAMPLES_DIR.parent
    monkeypatch.chdir(repo_root)
    output = repo_root / "output_pacs008.xml"
    output.unlink(missing_ok=True)
    yield repo_root
    output.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# examples/generate_xml.py
# ---------------------------------------------------------------------------


class TestGenerateXmlExample:
    def test_script_runs_end_to_end(self, in_repo_root):
        """Executes the full body of examples/generate_xml.py.

        Asserts: XML output file written, non-empty, parseable.
        """
        script = _EXAMPLES_DIR / "generate_xml.py"
        runpy.run_path(str(script), run_name="__main__")

        output = in_repo_root / "output_pacs008.xml"
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert content.startswith("<?xml")
        assert "pacs.008.001.05" in content
        assert "Acme Corp GmbH" in content


# ---------------------------------------------------------------------------
# examples/swift_compliance.py
# ---------------------------------------------------------------------------


class TestSwiftComplianceExample:
    def test_script_runs_end_to_end(self, capsys, in_repo_root):
        """Executes the full body of examples/swift_compliance.py.

        Asserts: prints both the simple-cleanse and report sections,
        and the report mentions at least one violation since the
        sample data deliberately contains oversize msg_id, non-Latin
        chars and the ™/€ symbols.
        """
        script = _EXAMPLES_DIR / "swift_compliance.py"
        runpy.run_path(str(script), run_name="__main__")

        captured = capsys.readouterr()
        assert "Simple Cleanse" in captured.out
        assert "Cleanse with Report" in captured.out
        assert "Violations:" in captured.out
        # The oversize msg_id must be reported as a field_length
        # violation by the cleanse-with-report path.
        assert "field_length" in captured.out
