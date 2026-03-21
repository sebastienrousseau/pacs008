"""Tests for pacs008.data.loader module."""

import pytest

from pacs008.data.loader import load_payment_data
from pacs008.exceptions import DataSourceError, PaymentValidationError


def _valid_data():
    return {
        "msg_id": "MSG001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
    }


class TestLoadFromList:
    def test_valid_list(self):
        data = load_payment_data([_valid_data()])
        assert len(data) == 1
        assert data[0]["msg_id"] == "MSG001"

    def test_empty_list_raises(self):
        with pytest.raises(DataSourceError, match="Empty"):
            load_payment_data([])

    def test_non_dict_items_raises(self):
        with pytest.raises(PaymentValidationError):
            load_payment_data(["not a dict"])

    def test_multiple_rows(self):
        row1 = _valid_data()
        row2 = _valid_data()
        row2["msg_id"] = "MSG002"
        data = load_payment_data([row1, row2])
        assert len(data) == 2


class TestLoadFromDict:
    def test_valid_dict(self):
        data = load_payment_data(_valid_data())
        assert len(data) == 1

    def test_empty_dict_raises(self):
        with pytest.raises(DataSourceError, match="Empty"):
            load_payment_data({})


class TestLoadFromFile:
    def test_unsupported_extension_raises(self):
        with pytest.raises(DataSourceError, match="Unsupported file type"):
            load_payment_data("data.txt")

    def test_nonexistent_csv_raises(self):
        with pytest.raises(FileNotFoundError):
            load_payment_data("/nonexistent/data.csv")


class TestUnsupportedType:
    def test_int_raises(self):
        with pytest.raises(DataSourceError, match="Unsupported data source"):
            load_payment_data(42)

    def test_none_raises(self):
        with pytest.raises(DataSourceError, match="Unsupported data source"):
            load_payment_data(None)
