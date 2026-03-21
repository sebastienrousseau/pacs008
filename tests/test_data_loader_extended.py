"""Extended tests for data/loader.py covering streaming and edge cases."""

import csv
import json
import os

import pytest

from pacs008.data.loader import (
    _load_from_dict,
    _load_from_file,
    _load_from_list,
    load_payment_data,
    load_payment_data_streaming,
)
from pacs008.exceptions import DataSourceError, PaymentValidationError


def _make_valid_row(**overrides):
    row = {
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
    row.update(overrides)
    return row


@pytest.fixture()
def valid_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.csv"
    row = _make_valid_row()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
    return str(path)


@pytest.fixture()
def valid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.json"
    path.write_text(json.dumps([_make_valid_row()]), encoding="utf-8")
    return str(path)


@pytest.fixture()
def valid_jsonl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.jsonl"
    path.write_text(json.dumps(_make_valid_row()) + "\n", encoding="utf-8")
    return str(path)


class TestLoadPaymentDataFromList:
    def test_valid_list(self):
        data = load_payment_data([_make_valid_row()])
        assert len(data) == 1

    def test_empty_list_raises(self):
        with pytest.raises(DataSourceError, match="Empty"):
            load_payment_data([])

    def test_non_dict_items_raises(self):
        with pytest.raises(PaymentValidationError, match="dictionaries"):
            load_payment_data(["not a dict"])


class TestLoadPaymentDataFromDict:
    def test_valid_dict(self):
        data = load_payment_data(_make_valid_row())
        assert len(data) == 1
        assert data[0]["msg_id"] == "MSG-001"

    def test_empty_dict_raises(self):
        with pytest.raises(DataSourceError, match="Empty"):
            load_payment_data({})


class TestLoadPaymentDataFromFile:
    def test_load_csv(self, valid_csv):
        data = load_payment_data(valid_csv)
        assert len(data) >= 1

    def test_load_json(self, valid_json):
        data = load_payment_data(valid_json)
        assert len(data) == 1

    def test_load_jsonl(self, valid_jsonl):
        data = load_payment_data(valid_jsonl)
        assert len(data) == 1

    def test_unsupported_extension(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "data.txt"
        path.write_text("hello")
        with pytest.raises(DataSourceError, match="Unsupported"):
            load_payment_data(str(path))

    def test_unsupported_type_raises(self):
        with pytest.raises(DataSourceError, match="Unsupported data source type"):
            load_payment_data(42)


class TestLoadPaymentDataStreaming:
    def test_stream_from_list(self):
        rows = [_make_valid_row(msg_id=f"MSG-{i}") for i in range(5)]
        chunks = list(load_payment_data_streaming(rows, chunk_size=2))
        assert len(chunks) == 3  # 2+2+1
        assert len(chunks[0]) == 2
        assert len(chunks[-1]) == 1

    def test_stream_empty_list_raises(self):
        with pytest.raises(DataSourceError, match="Empty"):
            list(load_payment_data_streaming([]))

    def test_stream_non_dict_items_raises(self):
        with pytest.raises(PaymentValidationError, match="dictionaries"):
            list(load_payment_data_streaming(["bad"]))

    def test_stream_unsupported_type_raises(self):
        with pytest.raises(DataSourceError, match="Unsupported"):
            list(load_payment_data_streaming(42))

    def test_stream_from_csv(self, valid_csv):
        chunks = list(load_payment_data_streaming(valid_csv, chunk_size=1))
        assert len(chunks) >= 1

    def test_stream_unsupported_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "data.txt"
        path.write_text("hello")
        with pytest.raises(DataSourceError, match="Unsupported"):
            list(load_payment_data_streaming(str(path)))


class TestLoadFromDict:
    def test_valid(self):
        data = _load_from_dict(_make_valid_row())
        assert len(data) == 1

    def test_empty(self):
        with pytest.raises(DataSourceError):
            _load_from_dict({})


class TestLoadFromList:
    def test_valid(self):
        data = _load_from_list([_make_valid_row()])
        assert len(data) == 1

    def test_empty(self):
        with pytest.raises(DataSourceError):
            _load_from_list([])
