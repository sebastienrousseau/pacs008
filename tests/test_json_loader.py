"""Tests for JSON and JSONL data loaders."""

import json

import pytest

from pacs008.exceptions import DataSourceError
from pacs008.json.load_json_data import (
    load_json_data,
    load_json_data_streaming,
    load_jsonl_data,
    load_jsonl_data_streaming,
)


@pytest.fixture()
def json_array_file(tmp_path, monkeypatch):
    """Create a JSON file with array of payment data."""
    monkeypatch.chdir(tmp_path)
    data = [
        {
            "msg_id": "MSG-001",
            "end_to_end_id": "E2E-001",
            "interbank_settlement_amount": "1000.00",
        },
        {
            "msg_id": "MSG-002",
            "end_to_end_id": "E2E-002",
            "interbank_settlement_amount": "500.00",
        },
    ]
    path = tmp_path / "payments.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture()
def json_single_file(tmp_path, monkeypatch):
    """Create a JSON file with single payment object."""
    monkeypatch.chdir(tmp_path)
    data = {"msg_id": "MSG-SINGLE", "end_to_end_id": "E2E-SINGLE"}
    path = tmp_path / "single.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture()
def jsonl_file(tmp_path, monkeypatch):
    """Create a JSONL file with multiple lines."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.jsonl"
    lines = [
        json.dumps({"msg_id": "MSG-L1", "amount": "100"}),
        "",  # empty line
        json.dumps({"msg_id": "MSG-L2", "amount": "200"}),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


class TestLoadJsonData:
    """Test JSON data loader."""

    def test_load_array_format(self, json_array_file):
        data = load_json_data(json_array_file)
        assert len(data) == 2
        assert data[0]["msg_id"] == "MSG-001"

    def test_load_single_object(self, json_single_file):
        data = load_json_data(json_single_file)
        assert len(data) == 1
        assert data[0]["msg_id"] == "MSG-SINGLE"

    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            load_json_data(str(tmp_path / "nonexistent.json"))

    def test_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "bad.json"
        path.write_text("{invalid json}", encoding="utf-8")
        with pytest.raises(DataSourceError, match="Invalid JSON"):
            load_json_data(str(path))

    def test_array_with_non_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "mixed.json"
        path.write_text('[{"ok": true}, "not_a_dict"]', encoding="utf-8")
        with pytest.raises(DataSourceError, match="must contain only objects"):
            load_json_data(str(path))

    def test_non_object_non_array(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "string.json"
        path.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(DataSourceError, match="object or array"):
            load_json_data(str(path))


class TestLoadJsonDataStreaming:
    """Test JSON streaming loader."""

    def test_yields_chunks(self, json_array_file):
        chunks = list(load_json_data_streaming(json_array_file, chunk_size=1))
        assert len(chunks) == 2
        assert len(chunks[0]) == 1

    def test_single_chunk(self, json_array_file):
        chunks = list(
            load_json_data_streaming(json_array_file, chunk_size=100)
        )
        assert len(chunks) == 1
        assert len(chunks[0]) == 2


class TestLoadJsonlData:
    """Test JSONL data loader."""

    def test_load_jsonl(self, jsonl_file):
        data = load_jsonl_data(jsonl_file)
        assert len(data) == 2
        assert data[0]["msg_id"] == "MSG-L1"

    def test_skips_empty_lines(self, jsonl_file):
        data = load_jsonl_data(jsonl_file)
        assert len(data) == 2  # empty line skipped

    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            load_jsonl_data(str(tmp_path / "nonexistent.jsonl"))

    def test_invalid_json_line(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "bad.jsonl"
        path.write_text('{"ok": true}\n{bad json}\n', encoding="utf-8")
        with pytest.raises(DataSourceError, match="Invalid JSON on line"):
            load_jsonl_data(str(path))

    def test_non_dict_line(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "array_line.jsonl"
        path.write_text("[1,2,3]\n", encoding="utf-8")
        with pytest.raises(DataSourceError, match="Expected JSON object"):
            load_jsonl_data(str(path))

    def test_empty_jsonl(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "empty.jsonl"
        path.write_text("\n\n", encoding="utf-8")
        with pytest.raises(DataSourceError, match="empty"):
            load_jsonl_data(str(path))


class TestLoadJsonlDataStreaming:
    """Test JSONL streaming loader."""

    def test_yields_chunks(self, jsonl_file):
        chunks = list(load_jsonl_data_streaming(jsonl_file, chunk_size=1))
        assert len(chunks) == 2

    def test_single_chunk(self, jsonl_file):
        chunks = list(load_jsonl_data_streaming(jsonl_file, chunk_size=100))
        assert len(chunks) == 1
        assert len(chunks[0]) == 2

    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            list(load_jsonl_data_streaming(str(tmp_path / "nope.jsonl")))

    def test_invalid_json_line(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "bad_stream.jsonl"
        path.write_text("{bad}\n", encoding="utf-8")
        with pytest.raises(DataSourceError):
            list(load_jsonl_data_streaming(str(path)))

    def test_non_dict_line(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "arr.jsonl"
        path.write_text('"string"\n', encoding="utf-8")
        with pytest.raises(DataSourceError):
            list(load_jsonl_data_streaming(str(path)))
