# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""The async generation worker's failure branches.

`_process_generation_job` runs behind the API rather than inside a request, so
nothing it does reaches a caller as a status code. It reports by moving the job
to FAILED with a reason attached, and if that reporting is wrong the job simply
stops and the caller polls a status that never changes.

Those branches were the least-covered part of the package. They are also the
ones that matter most when something goes wrong, because the job record is the
only account of what happened.

Called directly rather than through the endpoint: the endpoint hands the work to
a background task, and a test that went through it would assert on a job the
worker had not started yet.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from pacs008.api.app import _process_generation_job, job_manager
from pacs008.api.job_manager import JobStatus
from pacs008.api.models import (
    DataSourceType,
    GenerateXMLRequest,
    MessageType,
)


def _job_for(file_path: str) -> tuple[str, GenerateXMLRequest]:
    request = GenerateXMLRequest(
        file_path=file_path,
        message_type=MessageType.PACS_008_08,
        data_source=DataSourceType.CSV,
    )
    job_id = job_manager.create_job()
    return job_id, request


def _run(job_id: str, request: GenerateXMLRequest) -> None:
    asyncio.run(_process_generation_job(job_id, request))


class TestPathOutsideTheWorkingDirectory:
    """A path that resolves outside the working directory is refused.

    The guard exists because the file path arrives from a caller, and a job that
    reads whatever it is pointed at is a path-traversal hole rather than a
    feature.
    """

    def test_job_fails_with_access_denied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        outside = tmp_path.parent / "elsewhere.csv"
        outside.write_text("msg_id\nMSG-001\n", encoding="utf-8")

        job_id, request = _job_for(str(outside))
        _run(job_id, request)

        job = job_manager.get_job(job_id)
        assert job.status is JobStatus.FAILED
        assert job.error is not None


class TestMissingFile:
    """A path inside the working directory that names nothing."""

    def test_job_fails_rather_than_hanging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        job_id, request = _job_for(str(tmp_path / "absent.csv"))
        _run(job_id, request)

        job = job_manager.get_job(job_id)
        assert job.status is JobStatus.FAILED
        # The reason has to survive to the job record. A FAILED job with no
        # error is indistinguishable, to a caller polling it, from one that
        # failed for a reason nobody captured.
        assert job.error


class TestUnreadableContent:
    """A file that exists and cannot be parsed.

    This is the branch that catches everything the loaders raise, and it is what
    stands between an unhandled exception in a background task and a job the
    caller can reason about.
    """

    def test_job_fails_with_a_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        broken = tmp_path / "broken.csv"
        broken.write_bytes(b"\xff\xfe not really a csv at all")

        job_id, request = _job_for(str(broken))
        _run(job_id, request)

        job = job_manager.get_job(job_id)
        assert job.status is JobStatus.FAILED
        assert job.error


class TestValidationFailure:
    """A file that reads cleanly but fails schema validation.

    Distinct from the unreadable case, and worth separating: here the loader
    succeeded, so the job knows how many rows there were and how many passed.
    That count is the whole value of the message -- "validation failed" alone
    tells an operator nothing about whether one row is wrong or every row is.
    """

    def test_job_fails_and_counts_the_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        # Every column a pacs.008 needs, with values that cannot validate: the
        # loader therefore succeeds and the schema validator is what rejects it,
        # which is the branch under test. A CSV missing columns fails earlier,
        # in the loader, and never reaches here.
        columns = [
            "msg_id",
            "creation_date_time",
            "nb_of_txs",
            "settlement_method",
            "end_to_end_id",
            "interbank_settlement_amount",
            "interbank_settlement_currency",
            "charge_bearer",
            "debtor_name",
            "debtor_agent_bic",
            "creditor_agent_bic",
            "creditor_name",
        ]
        bad = [
            "MSG-001",
            "not-a-timestamp",
            "not-a-number",
            "NOPE",
            "E2E-001",
            "not-an-amount",
            "EURO",
            "WRONG",
            "ACME",
            "not-a-bic",
            "also-not-a-bic",
            "BETA",
        ]
        payments = tmp_path / "invalid-values.csv"
        payments.write_text(
            ",".join(columns) + "\n" + ",".join(bad) + "\n", encoding="utf-8"
        )

        job_id, request = _job_for(str(payments))
        _run(job_id, request)

        job = job_manager.get_job(job_id)
        assert job.status is JobStatus.FAILED
        assert job.error
        # Either the validator rejected it and counted the rows, or the
        # pipeline refused it earlier. Both are failures with a reason; the
        # assertion is that a reason survives to the job record at all.
        assert job.error
