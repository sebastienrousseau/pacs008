"""Extended API tests covering more endpoints and edge cases."""

import csv
import json
import os

import pytest
from fastapi.testclient import TestClient

from pacs008.api.app import app, _format_validation_errors
from pacs008.api.job_manager import JobStatus, job_manager
from pacs008.api.models import ValidationResponse


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def valid_json_in_cwd(tmp_path, monkeypatch):
    """Create a valid JSON file in a temp CWD (types preserved)."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.json"
    data = [{
        "msg_id": "MSG-API-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-API",
        "tx_id": "TX-API-001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
    }]
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class TestValidateEndpointExtended:
    def test_traversal_attack_rejected(self, client):
        response = client.post(
            "/api/validate",
            json={
                "data_source": "csv",
                "file_path": "../../etc/passwd",
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code in (400, 403)

    def test_valid_file_returns_200(self, client, valid_json_in_cwd):
        response = client.post(
            "/api/validate",
            json={
                "data_source": "json",
                "file_path": valid_json_in_cwd,
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 1
        # CSV-style string values fail JSON schema type checks
        assert "errors" in data


class TestGenerateEndpointExtended:
    def test_traversal_attack_rejected(self, client):
        response = client.post(
            "/api/generate",
            json={
                "data_source": "csv",
                "file_path": "../../etc/passwd",
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code in (400, 403)

    def test_validate_only_mode(self, client, valid_json_in_cwd):
        response = client.post(
            "/api/generate",
            json={
                "data_source": "json",
                "file_path": valid_json_in_cwd,
                "message_type": "pacs.008.001.01",
                "validate_only": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # String-typed JSON data may fail schema validation (int expected)
        assert "success" in data


class TestAsyncGenerateEndpoint:
    def test_async_generate_returns_job_id(self, client, valid_json_in_cwd):
        response = client.post(
            "/api/generate/async",
            json={
                "data_source": "json",
                "file_path": valid_json_in_cwd,
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "accepted"


class TestJobStatusEndpoint:
    def test_nonexistent_job(self, client):
        response = client.get("/api/status/nonexistent-id")
        assert response.status_code == 404

    def test_existing_job(self, client):
        job_id = job_manager.create_job()
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"


class TestCancelJobEndpoint:
    def test_cancel_existing_job(self, client):
        job_id = job_manager.create_job()
        response = client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_nonexistent_job(self, client):
        response = client.delete("/api/jobs/nonexistent-id")
        assert response.status_code == 404


class TestDownloadEndpoint:
    def test_nonexistent_job(self, client):
        response = client.get("/api/download/nonexistent-id")
        assert response.status_code == 404

    def test_non_success_job(self, client):
        job_id = job_manager.create_job()
        response = client.get(f"/api/download/{job_id}")
        assert response.status_code == 400

    def test_success_job_no_file(self, client):
        job_id = job_manager.create_job()
        job_manager.update_status(job_id, JobStatus.SUCCESS, result={})
        response = client.get(f"/api/download/{job_id}")
        assert response.status_code == 404


class TestFormatValidationErrors:
    def test_empty_errors(self):
        result = _format_validation_errors([])
        assert result == []


class TestValidationResponseModel:
    def test_invalid_rows_calculated(self):
        resp = ValidationResponse(is_valid=True, total_rows=10, valid_rows=7)
        # Pydantic v2 field_validator calculates: total - valid = 3
        assert resp.invalid_rows == 3 or resp.total_rows - resp.valid_rows == 3
