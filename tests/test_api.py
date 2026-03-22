"""Tests for pacs008.api.app module."""

import pytest
from fastapi.testclient import TestClient

from pacs008.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    @pytest.mark.smoke
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_message(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "Pacs008" in data["message"]


class TestValidateEndpoint:
    def test_missing_file_returns_error(self, client):
        response = client.post(
            "/api/validate",
            json={
                "data_source": "csv",
                "file_path": "/nonexistent/data.csv",
                "message_type": "pacs.008.001.01",
            },
        )
        # Should fail with 400 or 404
        assert response.status_code in (400, 403, 404)


class TestGenerateEndpoint:
    def test_missing_file_returns_error(self, client):
        response = client.post(
            "/api/generate",
            json={
                "data_source": "csv",
                "file_path": "/nonexistent/data.csv",
                "message_type": "pacs.008.001.01",
            },
        )
        assert response.status_code in (400, 403, 404)


class TestDocsEndpoint:
    def test_docs_available(self, client):
        response = client.get("/api/docs")
        assert response.status_code == 200
