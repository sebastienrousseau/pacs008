"""Tests for db/load_db_data.py, db/load_db_data_streaming.py, db/validate_db_data.py."""

import sqlite3

import pytest

from pacs008.db.load_db_data import load_db_data, sanitize_table_name
from pacs008.db.load_db_data_streaming import load_db_data_streaming
from pacs008.db.validate_db_data import validate_db_data
from pacs008.exceptions import ConfigurationError, DataSourceError


def _make_valid_row():
    return {
        "msg_id": "MSG-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
    }


def _create_test_db(db_path, table_name="pacs008", rows=None):
    if rows is None:
        rows = [_make_valid_row()]
    conn = sqlite3.connect(str(db_path))
    cols = list(rows[0].keys())
    col_defs = ", ".join(f"{c} TEXT" for c in cols)
    conn.execute(f"CREATE TABLE {table_name} ({col_defs})")
    placeholders = ", ".join("?" for _ in cols)
    for row in rows:
        conn.execute(
            f"INSERT INTO {table_name} VALUES ({placeholders})",
            [row[c] for c in cols],
        )
    conn.commit()
    conn.close()


class TestSanitizeTableName:
    def test_valid_name(self):
        assert sanitize_table_name("pacs008") == "pacs008"

    def test_valid_with_underscore(self):
        assert sanitize_table_name("payment_data") == "payment_data"

    def test_empty_raises(self):
        with pytest.raises(ConfigurationError, match="empty"):
            sanitize_table_name("")

    def test_starts_with_number(self):
        with pytest.raises(ConfigurationError, match="Invalid"):
            sanitize_table_name("123table")

    def test_sql_injection_attempt(self):
        with pytest.raises(ConfigurationError, match="Invalid"):
            sanitize_table_name("table; DROP TABLE users")

    def test_special_chars(self):
        with pytest.raises(ConfigurationError, match="Invalid"):
            sanitize_table_name("table-name")

    def test_dot_rejected(self):
        with pytest.raises(ConfigurationError, match="Invalid"):
            sanitize_table_name("schema.table")


class TestLoadDbData:
    def test_load_valid_db(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        data = load_db_data(str(db_path), "pacs008")
        assert len(data) == 1
        assert data[0]["msg_id"] == "MSG-001"

    def test_load_multiple_rows(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "multi.db"
        rows = [{**_make_valid_row(), "msg_id": f"MSG-{i}"} for i in range(5)]
        _create_test_db(db_path, rows=rows)
        data = load_db_data(str(db_path), "pacs008")
        assert len(data) == 5

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_db_data("/nonexistent/test.db", "pacs008")

    def test_invalid_table_name_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        with pytest.raises(ConfigurationError):
            load_db_data(str(db_path), "1invalid")

    def test_traversal_raises(self):
        with pytest.raises(FileNotFoundError):
            load_db_data("../../etc/passwd", "pacs008")


class TestLoadDbDataStreaming:
    def test_stream_valid_db(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "stream.db"
        rows = [{**_make_valid_row(), "msg_id": f"MSG-{i}"} for i in range(5)]
        _create_test_db(db_path, rows=rows)
        chunks = list(
            load_db_data_streaming(str(db_path), "pacs008", chunk_size=2)
        )
        assert len(chunks) == 3  # 2+2+1
        assert len(chunks[0]) == 2
        assert len(chunks[-1]) == 1

    def test_stream_single_chunk(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "single.db"
        _create_test_db(db_path)
        chunks = list(
            load_db_data_streaming(str(db_path), "pacs008", chunk_size=100)
        )
        assert len(chunks) == 1

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            list(load_db_data_streaming("/nonexistent/test.db", "pacs008"))

    def test_empty_table_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE pacs008 (msg_id TEXT)")
        conn.commit()
        conn.close()
        with pytest.raises(DataSourceError, match="empty"):
            list(load_db_data_streaming(str(db_path), "pacs008"))

    def test_nonexistent_table_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "notable.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE other (col TEXT)")
        conn.commit()
        conn.close()
        with pytest.raises(DataSourceError, match="does not exist"):
            list(load_db_data_streaming(str(db_path), "pacs008"))

    def test_invalid_table_name_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        with pytest.raises(ConfigurationError):
            list(load_db_data_streaming(str(db_path), "1invalid"))


class TestValidateDbData:
    def test_valid_data(self):
        assert validate_db_data([_make_valid_row()])

    def test_valid_multiple(self):
        assert validate_db_data([_make_valid_row(), _make_valid_row()])

    def test_missing_required_field(self):
        row = _make_valid_row()
        del row["msg_id"]
        assert not validate_db_data([row])

    def test_none_value(self):
        row = _make_valid_row()
        row["msg_id"] = None
        assert not validate_db_data([row])

    def test_empty_value(self):
        row = _make_valid_row()
        row["debtor_name"] = ""
        assert not validate_db_data([row])

    def test_empty_list(self):
        assert validate_db_data([])

    def test_missing_settlement_method(self):
        row = _make_valid_row()
        del row["settlement_method"]
        assert not validate_db_data([row])

    def test_missing_amount(self):
        row = _make_valid_row()
        del row["interbank_settlement_amount"]
        assert not validate_db_data([row])
