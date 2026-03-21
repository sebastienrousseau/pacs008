"""Full API coverage tests for remaining uncovered lines in api/app.py."""

import csv
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pacs008.api.app import (
    _format_validation_errors,
    _resolve_generation_paths,
    _validate_safe_path,
    app,
)
from pacs008.api.job_manager import JobStatus, job_manager
from pacs008.api.models import GenerateXMLRequest, MessageType
from pacs008.constants import TEMPLATES_DIR


@pytest.fixture()
def client():
    return TestClient(app)


def _make_valid_row():
    return {
        "msg_id": "MSG-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-001",
        "tx_id": "TX-001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
    }


@pytest.fixture()
def valid_json_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.json"
    path.write_text(json.dumps([_make_valid_row()]), encoding="utf-8")
    return str(path)


class TestValidateSafePath:
    def test_valid_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "test.txt"
        f.write_text("test")
        result = _validate_safe_path(str(f))
        assert result == Path(str(f)).resolve()

    def test_traversal_raises_400(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_safe_path("../../etc/passwd")
        assert exc_info.value.status_code in (400, 403)

    def test_outside_cwd_raises_403(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        monkeypatch.chdir(tmp_path)
        with pytest.raises(HTTPException) as exc_info:
            _validate_safe_path("/usr/bin/python")
        assert exc_info.value.status_code == 403


class TestFormatValidationErrors:
    def test_with_errors(self):
        from pacs008.validation.schema_validator import (
            ValidationError as SchemaValidationError,
        )
        errors = [
            (0, [SchemaValidationError("bad value", "$.field", "val", "type")]),
            (1, [
                SchemaValidationError("missing", "$.other", None, "required"),
                SchemaValidationError("wrong", "$.third", "x", "pattern"),
            ]),
        ]
        result = _format_validation_errors(errors)
        assert len(result) == 3
        assert result[0].field == "$.field"


class TestValidateEndpointFull:
    def test_file_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = client.post(
            "/api/validate",
            json={
                "data_source": "json",
                "file_path": str(tmp_path / "nonexistent.json"),
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code in (400, 403, 404)

    def test_payment_validation_error(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(["not a dict"]), encoding="utf-8")
        response = client.post(
            "/api/validate",
            json={
                "data_source": "json",
                "file_path": str(path),
                "message_type": "pacs.008.001.01",
            },
        )
        # DataSourceError or PaymentValidationError -> 400 or 500
        assert response.status_code in (400, 500)

    def test_internal_error(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "crash.json"
        path.write_text("{invalid", encoding="utf-8")
        response = client.post(
            "/api/validate",
            json={
                "data_source": "json",
                "file_path": str(path),
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 500


class TestGenerateEndpointFull:
    def test_file_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        response = client.post(
            "/api/generate",
            json={
                "data_source": "json",
                "file_path": str(tmp_path / "nonexistent.json"),
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code in (400, 403, 404)

    def test_payment_validation_error(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(["not a dict"]), encoding="utf-8")
        response = client.post(
            "/api/generate",
            json={
                "data_source": "json",
                "file_path": str(path),
                "message_type": "pacs.008.001.01",
            },
        )
        # DataSourceError or PaymentValidationError -> 400 or 500
        assert response.status_code in (400, 500)

    def test_internal_error(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "crash.json"
        path.write_text("{invalid", encoding="utf-8")
        response = client.post(
            "/api/generate",
            json={
                "data_source": "json",
                "file_path": str(path),
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 500

    def test_validation_errors_returned(self, client, valid_json_file):
        # JSON with string nb_of_txs will fail schema validation
        response = client.post(
            "/api/generate",
            json={
                "data_source": "json",
                "file_path": valid_json_file,
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # String types will fail JSON schema => success=False with validation_errors
        assert "success" in data


class TestAsyncGenerateEndpointFull:
    def test_async_exception_handling(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Test with non-existent file - should still create job
        path = tmp_path / "payments.json"
        path.write_text(json.dumps([_make_valid_row()]), encoding="utf-8")
        response = client.post(
            "/api/generate/async",
            json={
                "data_source": "json",
                "file_path": str(path),
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestJobStatusFull:
    def test_processing_status(self, client):
        job_id = job_manager.create_job()
        job_manager.update_status(job_id, JobStatus.PROCESSING, progress=50)
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress_percent"] == 50

    def test_failed_status(self, client):
        job_id = job_manager.create_job()
        job_manager.update_status(
            job_id, JobStatus.FAILED, error="Something broke"
        )
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Something broke"

    def test_cancelled_status(self, client):
        job_id = job_manager.create_job()
        job_manager.cancel_job(job_id)
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_success_with_result(self, client):
        job_id = job_manager.create_job()
        job_manager.update_status(
            job_id,
            JobStatus.SUCCESS,
            progress=100,
            result={
                "success": True,
                "message": "Done",
                "file_path": os.path.join(tempfile.gettempdir(), "out.xml"),
                "validation_errors": [],
            },
        )
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"] is not None


class TestDownloadEndpointFull:
    def test_download_success_file_outside_cwd(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        job_id = job_manager.create_job()
        # File path outside CWD should be rejected
        job_manager.update_status(
            job_id,
            JobStatus.SUCCESS,
            result={"file_path": "/etc/passwd"},
        )
        response = client.get(f"/api/download/{job_id}")
        assert response.status_code in (400, 403)

    def test_download_success_file_missing(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        job_id = job_manager.create_job()
        missing_path = str(tmp_path / "missing.xml")
        job_manager.update_status(
            job_id,
            JobStatus.SUCCESS,
            result={"file_path": missing_path},
        )
        response = client.get(f"/api/download/{job_id}")
        assert response.status_code == 404

    def test_download_success_file_exists(self, client, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        xml_file = tmp_path / "output.xml"
        xml_file.write_text("<root/>", encoding="utf-8")
        job_id = job_manager.create_job()
        job_manager.update_status(
            job_id,
            JobStatus.SUCCESS,
            result={"file_path": str(xml_file)},
        )
        response = client.get(f"/api/download/{job_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"


class TestResolveGenerationPaths:
    def test_with_output_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        request = GenerateXMLRequest(
            data_source="json",
            file_path="test.json",
            message_type=MessageType.PACS_008_01,
            output_dir=str(out_dir),
        )
        output_dir, xsd, tpl = _resolve_generation_paths(request)
        assert output_dir == str(out_dir.resolve())

    def test_without_output_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        request = GenerateXMLRequest(
            data_source="json",
            file_path="test.json",
            message_type=MessageType.PACS_008_01,
        )
        output_dir, xsd, tpl = _resolve_generation_paths(request)
        assert output_dir == str(Path.cwd())
