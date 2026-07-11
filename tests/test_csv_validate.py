"""Tests for pacs008.csv.validate_csv_data module."""

from pacs008.csv.validate_csv_data import (
    _validate_field_type,
    validate_csv_data,
)


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


# --- Native (JSON/JSONL) scalar handling -----------------------------------
# JSON payloads carry native int/float/bool, not strings. The validator must
# accept them without raising AttributeError on .strip()/.lower()/.endswith.


def test_native_int_and_float_pass():
    """A JSON row with native int/float values validates (regression)."""
    row = _valid_row()
    row["nb_of_txs"] = 1
    row["interbank_settlement_amount"] = 25000.00
    assert validate_csv_data([row]) is True


def test_native_zero_is_present_not_missing():
    """Native 0 / 0.0 are real values, not missing columns."""
    row = _valid_row()
    row["nb_of_txs"] = 0
    row["interbank_settlement_amount"] = 0.0
    assert validate_csv_data([row]) is True


def test_non_integral_float_for_int_field_fails():
    """A native non-integral float in an int field is invalid."""
    row = _valid_row()
    row["nb_of_txs"] = 1.5
    assert validate_csv_data([row]) is False


def test_native_bool_for_int_field_fails():
    """A native bool must not satisfy an int field (bool subclasses int)."""
    row = _valid_row()
    row["nb_of_txs"] = True
    assert validate_csv_data([row]) is False


def test_non_string_datetime_is_invalid_not_crash():
    """A non-string value for a datetime field is invalid, not a crash."""
    row = _valid_row()
    row["creation_date_time"] = 20260115
    assert validate_csv_data([row]) is False


def test_whitespace_only_string_is_missing():
    """A whitespace-only string is treated as a missing value."""
    row = _valid_row()
    row["creditor_name"] = "   "
    assert validate_csv_data([row]) is False


def test_native_scalar_for_string_field_is_accepted():
    """A present native scalar satisfies a string field (lenient, no crash)."""
    row = _valid_row()
    row["msg_id"] = 12345
    assert validate_csv_data([row]) is True


# --- _validate_field_type unit coverage (bool has no field in the schema) ---


def test_field_type_bool_accepts_native_and_string_forms():
    assert _validate_field_type(True, bool) is True
    assert _validate_field_type(False, bool) is True
    assert _validate_field_type("true", bool) is True
    assert _validate_field_type("FALSE", bool) is True
    assert _validate_field_type("yes", bool) is False
    assert _validate_field_type(1, bool) is False  # int is not a bool


def test_field_type_float_rejects_native_bool():
    assert _validate_field_type(True, float) is False
