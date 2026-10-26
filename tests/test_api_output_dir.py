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

"""The API writes generated XML to ``output_dir``, never beside a template.

Before the fix, both the synchronous and the asynchronous endpoint resolved
``output_dir`` and then discarded it, writing ``<version>.xml`` into
``pacs008/templates/<version>/`` under the working directory: in a source
checkout that overwrote the shipped sample.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pacs008.api.app import app

VERSION = "pacs.008.001.08"
CSV = (
    "msg_id,creation_date_time,nb_of_txs,settlement_method,end_to_end_id,"
    "interbank_settlement_amount,interbank_settlement_currency,charge_bearer,"
    "debtor_name,debtor_agent_bic,creditor_agent_bic,creditor_name,uetr\n"
    "M1,2026-06-13T10:30:00,1,CLRG,E2E,100.00,EUR,SHAR,Alice,"
    "DEUTDEFF,BNPAFRPP,Bob,f47ac10b-58cc-4372-a567-0e02b2c3d479\n"
)


def _digests(directory: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.iterdir())
    }


@pytest.fixture
def workspace(template_copy, tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A working directory with the version's templates and one CSV row."""
    template_copy(VERSION)
    (tmp_path / "payments.csv").write_text(CSV)
    templates = tmp_path / "pacs008" / "templates" / VERSION
    return templates, _digests(templates)


def _request(**extra: object) -> dict[str, object]:
    return {
        "file_path": str(Path.cwd() / "payments.csv"),
        "data_source": "csv",
        "message_type": VERSION,
        **extra,
    }


def test_generate_writes_into_output_dir(workspace) -> None:
    templates, before = workspace
    response = TestClient(app).post(
        "/api/generate", json=_request(output_dir="out")
    )
    assert response.status_code == 200, response.text
    expected = (Path.cwd() / "out" / f"{VERSION}.xml").resolve()
    assert response.json()["file_path"] == str(expected)
    assert expected.read_text(encoding="utf-8").lstrip().startswith("<")
    assert _digests(templates) == before


def test_generate_defaults_to_the_working_directory(workspace) -> None:
    templates, before = workspace
    response = TestClient(app).post("/api/generate", json=_request())
    assert response.status_code == 200, response.text
    expected = Path.cwd().resolve() / f"{VERSION}.xml"
    assert response.json()["file_path"] == str(expected)
    assert expected.is_file()
    assert _digests(templates) == before


def test_async_job_writes_into_output_dir(workspace) -> None:
    templates, before = workspace
    client = TestClient(app)
    submit = client.post(
        "/api/generate/async", json=_request(output_dir="jobs")
    )
    assert submit.status_code == 200, submit.text
    status = client.get(f"/api/status/{submit.json()['job_id']}").json()
    expected = (Path.cwd() / "jobs" / f"{VERSION}.xml").resolve()
    assert status["result"]["file_path"] == str(expected), status
    assert expected.is_file()
    assert _digests(templates) == before
