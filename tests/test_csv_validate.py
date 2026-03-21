"""Tests for pacs008.csv.validate_csv_data module."""

from pacs008.csv.validate_csv_data import validate_csv_data


def _valid_row():
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


def test_valid_data_passes():
    assert validate_csv_data([_valid_row()]) is True


def test_empty_data_fails():
    assert validate_csv_data([]) is False


def test_missing_required_column_fails():
    row = _valid_row()
    del row["msg_id"]
    assert validate_csv_data([row]) is False


def test_invalid_nb_of_txs_type_fails():
    row = _valid_row()
    row["nb_of_txs"] = "not_a_number"
    assert validate_csv_data([row]) is False


def test_invalid_amount_type_fails():
    row = _valid_row()
    row["interbank_settlement_amount"] = "abc"
    assert validate_csv_data([row]) is False


def test_invalid_datetime_fails():
    row = _valid_row()
    row["creation_date_time"] = "not-a-date"
    assert validate_csv_data([row]) is False


def test_empty_string_field_fails():
    row = _valid_row()
    row["debtor_name"] = ""
    assert validate_csv_data([row]) is False


def test_multiple_valid_rows():
    rows = [_valid_row(), _valid_row()]
    assert validate_csv_data(rows) is True


def test_utc_datetime_with_z_passes():
    row = _valid_row()
    row["creation_date_time"] = "2026-01-15T10:30:00Z"
    assert validate_csv_data([row]) is True


def test_date_only_passes():
    row = _valid_row()
    row["creation_date_time"] = "2026-01-15"
    assert validate_csv_data([row]) is True
