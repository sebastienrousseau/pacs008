# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""`load_payment_data` given data rather than a file path.

The loader takes a path, a list of dictionaries, or a single dictionary. The
file paths are exercised everywhere; the in-memory forms are what a service
embedding this package actually uses, because it already has the rows and has no
reason to write a CSV first — and they were the least covered of the three.

The validation rejections matter more than the acceptances. A caller passing
rows that do not validate needs to be stopped here, at the boundary, rather than
have the failure surface later as malformed XML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pacs008.data.loader import (
    load_payment_data,
    load_payment_data_streaming,
)
from pacs008.exceptions import DataSourceError, PaymentValidationError


def _valid_row() -> dict[str, Any]:
    """One row carrying every mandatory field, so validation passes."""
    return {
        "msg_id": "MSG-001",
        "creation_date_time": "2026-08-28T09:00:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SLEV",
        "debtor_name": "ACME Ltd",
        "debtor_agent_bic": "BANKGB2LXXX",
        "creditor_agent_bic": "BANKDEFFXXX",
        "creditor_name": "Beta GmbH",
    }


class TestList:
    def test_a_list_of_rows_is_returned_as_given(self) -> None:
        rows = [_valid_row()]
        assert load_payment_data(rows) == rows

    def test_an_empty_list_is_refused(self) -> None:
        with pytest.raises(
            (DataSourceError, PaymentValidationError, ValueError)
        ):
            load_payment_data([])

    def test_a_list_containing_something_other_than_a_row_is_refused(
        self,
    ) -> None:
        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            load_payment_data([_valid_row(), "not a row"])  # type: ignore[list-item]

    def test_rows_that_do_not_validate_are_refused(self) -> None:
        incomplete = {"msg_id": "MSG-001"}
        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            load_payment_data([incomplete])


class TestDict:
    def test_a_single_row_is_wrapped_in_a_list(self) -> None:
        row = _valid_row()
        assert load_payment_data(row) == [row]

    def test_an_empty_dictionary_is_refused(self) -> None:
        with pytest.raises(
            (DataSourceError, PaymentValidationError, ValueError)
        ):
            load_payment_data({})

    def test_a_row_that_does_not_validate_is_refused(self) -> None:
        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            load_payment_data({"msg_id": "MSG-001"})


class TestStreaming:
    """The streaming loader validates each chunk as it goes.

    It has to fail on the chunk rather than at the end: a caller processing
    chunk one has already acted on it by the time chunk four arrives, so the
    error names the index where the bad rows begin.
    """

    def test_valid_rows_stream_in_chunks(self) -> None:
        rows = [_valid_row() for _ in range(5)]
        chunks = list(load_payment_data_streaming(rows, chunk_size=2))
        assert [len(c) for c in chunks] == [2, 2, 1]

    def test_a_bad_chunk_stops_the_stream(self) -> None:
        rows = [_valid_row(), _valid_row(), {"msg_id": "MSG-003"}]
        stream = load_payment_data_streaming(rows, chunk_size=2, validate=True)

        # The first chunk is good and arrives; the second is not and raises.
        assert len(next(stream)) == 2
        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            list(stream)

    def test_validation_can_be_turned_off(self) -> None:
        # Deliberate: a caller that has already validated upstream should not
        # pay for it twice, and the loader is not the only place rows are
        # checked.
        rows = [{"msg_id": "MSG-001"}]
        chunks = list(load_payment_data_streaming(rows, validate=False))
        assert chunks == [rows]

    def test_a_list_with_a_non_row_is_refused_before_streaming(self) -> None:
        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            list(load_payment_data_streaming([_valid_row(), 42]))  # type: ignore[list-item]


class TestStreamingFromAFile:
    """The same validation, reached through a file rather than a list.

    A different branch from the in-memory one: the rows arrive from a format
    loader, so the error names the format and the file as well as the chunk.
    That is what makes it actionable when a nightly batch fails at 3am against
    one file out of forty.
    """

    def test_a_file_whose_rows_do_not_validate_stops_the_stream(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        payments = tmp_path / "incomplete.csv"
        payments.write_text("msg_id\nMSG-001\nMSG-002\n", encoding="utf-8")

        with pytest.raises(
            (PaymentValidationError, DataSourceError, ValueError)
        ):
            list(load_payment_data_streaming(str(payments), chunk_size=1))

    def test_the_same_file_streams_when_validation_is_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        payments = tmp_path / "incomplete-novalidate.csv"
        payments.write_text("msg_id\nMSG-001\nMSG-002\n", encoding="utf-8")

        chunks = list(
            load_payment_data_streaming(
                str(payments), chunk_size=1, validate=False
            )
        )
        assert [row["msg_id"] for chunk in chunks for row in chunk] == [
            "MSG-001",
            "MSG-002",
        ]
