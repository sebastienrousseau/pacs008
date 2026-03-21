"""Tests for pacs008.api.models module."""

from pacs008.api.models import (
    DataSourceType,
    GenerateXMLRequest,
    GenerateXMLResponse,
    HealthResponse,
    MessageType,
    ValidationRequest,
    ValidationResponse,
)


class TestMessageType:
    def test_has_13_members(self):
        assert len(MessageType) == 13

    def test_values_format(self):
        for mt in MessageType:
            assert mt.value.startswith("pacs.008.001.")

    def test_v01(self):
        assert MessageType.PACS_008_01.value == "pacs.008.001.01"

    def test_v13(self):
        assert MessageType.PACS_008_13.value == "pacs.008.001.13"


class TestDataSourceType:
    def test_csv(self):
        assert DataSourceType.CSV.value == "csv"

    def test_sqlite(self):
        assert DataSourceType.SQLITE.value == "sqlite"

    def test_parquet(self):
        assert DataSourceType.PARQUET.value == "parquet"


class TestValidationRequest:
    def test_create(self):
        req = ValidationRequest(
            data_source=DataSourceType.CSV,
            file_path="/tmp/data.csv",
            message_type=MessageType.PACS_008_01,
        )
        assert req.file_path == "/tmp/data.csv"


class TestGenerateXMLRequest:
    def test_create_with_defaults(self):
        req = GenerateXMLRequest(
            data_source=DataSourceType.CSV,
            file_path="/tmp/data.csv",
        )
        assert req.validate_only is False
        assert req.output_dir is None

    def test_validate_only(self):
        req = GenerateXMLRequest(
            data_source=DataSourceType.CSV,
            file_path="/tmp/data.csv",
            validate_only=True,
        )
        assert req.validate_only is True


class TestValidationResponse:
    def test_create_response(self):
        resp = ValidationResponse(
            is_valid=False,
            total_rows=10,
            valid_rows=7,
        )
        assert resp.total_rows == 10
        assert resp.valid_rows == 7

    def test_all_valid(self):
        resp = ValidationResponse(
            is_valid=True,
            total_rows=5,
            valid_rows=5,
        )
        assert resp.total_rows == 5


class TestGenerateXMLResponse:
    def test_success(self):
        resp = GenerateXMLResponse(
            success=True,
            message="OK",
            file_path="/tmp/output.xml",
        )
        assert resp.success
        assert resp.file_path == "/tmp/output.xml"


class TestHealthResponse:
    def test_create(self):
        resp = HealthResponse(
            status="healthy",
            version="0.0.1",
            message="running",
        )
        assert resp.status == "healthy"
