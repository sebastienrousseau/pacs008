"""Tests for CSV data loader and streaming."""

import csv

import pytest

from pacs008.csv.load_csv_data import load_csv_data, load_csv_data_streaming
from pacs008.exceptions import DataSourceError


@pytest.fixture()
def csv_file(tmp_path, monkeypatch):
    """Create a CSV file with payment data."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "amount", "currency"])
        writer.writeheader()
        writer.writerow(
            {"msg_id": "MSG-001", "amount": "1000.00", "currency": "EUR"}
        )
        writer.writerow(
            {"msg_id": "MSG-002", "amount": "500.00", "currency": "USD"}
        )
    return str(path)


@pytest.fixture()
def large_csv(tmp_path, monkeypatch):
    """Create a CSV file with many rows for streaming tests."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "large.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "amount"])
        writer.writeheader()
        for i in range(50):
            writer.writerow(
                {"msg_id": f"MSG-{i:04d}", "amount": f"{i * 100}.00"}
            )
    return str(path)


@pytest.fixture()
def empty_csv(tmp_path, monkeypatch):
    """Create an empty CSV file (headers only)."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "empty.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "amount"])
        writer.writeheader()
    return str(path)


class TestLoadCsvData:
    """Test CSV data loader."""

    def test_load_valid_csv(self, csv_file):
        data = load_csv_data(csv_file)
        assert len(data) == 2
        assert data[0]["msg_id"] == "MSG-001"
        assert data[1]["currency"] == "USD"

    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(
            Exception
        ):  # FileNotFoundError or path validation error
            load_csv_data(str(tmp_path / "nonexistent.csv"))

    def test_empty_csv_raises(self, empty_csv):
        with pytest.raises(DataSourceError, match="empty"):
            load_csv_data(empty_csv)

    def test_returns_list_of_dicts(self, csv_file):
        data = load_csv_data(csv_file)
        assert isinstance(data, list)
        assert all(isinstance(row, dict) for row in data)


class TestLoadCsvDataStreaming:
    """Test CSV streaming loader."""

    def test_yields_chunks(self, large_csv):
        chunks = list(load_csv_data_streaming(large_csv, chunk_size=10))
        assert len(chunks) == 5  # 50 rows / 10 per chunk
        assert len(chunks[0]) == 10

    def test_last_chunk_partial(self, large_csv):
        chunks = list(load_csv_data_streaming(large_csv, chunk_size=15))
        assert len(chunks) == 4  # 15+15+15+5
        assert len(chunks[-1]) == 5

    def test_single_chunk(self, large_csv):
        chunks = list(load_csv_data_streaming(large_csv, chunk_size=100))
        assert len(chunks) == 1
        assert len(chunks[0]) == 50

    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(Exception):
            list(load_csv_data_streaming(str(tmp_path / "nonexistent.csv")))

    def test_empty_csv_raises(self, empty_csv):
        with pytest.raises(DataSourceError, match="empty"):
            list(load_csv_data_streaming(empty_csv))

    def test_default_chunk_size(self, csv_file):
        chunks = list(load_csv_data_streaming(csv_file))
        assert len(chunks) == 1  # 2 rows < default 1000
