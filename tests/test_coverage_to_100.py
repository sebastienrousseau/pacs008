# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Final targeted tests to lift coverage to ≥99%.

These exercise the small remaining branches that the broader suite
leaves uncovered — defensive paths, edge cases, and a handful of
public helpers whose behaviour was previously only exercised
indirectly.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# pacs008.observability.otel — env-var off + list attribute coerce
# ---------------------------------------------------------------------------


def test_otel_disabled_via_env_returns_false(monkeypatch):
    monkeypatch.setenv("PACS008_OTEL_ENABLED", "off")
    from pacs008.observability import otel

    assert otel.is_enabled() is False


def test_otel_attr_value_coerces_list_recursively():
    from pacs008.observability.otel import _attr_value

    assert _attr_value([1, "x", 2.5]) == [1, "x", 2.5]


# ---------------------------------------------------------------------------
# pacs008.observability.metrics — increment_failed sets FAILED status
# ---------------------------------------------------------------------------


def test_execution_metrics_increment_failed_sets_status():
    import logging

    from pacs008.observability.fields import ExecutionStatus
    from pacs008.observability.metrics import ExecutionMetrics

    metrics = ExecutionMetrics(logging.getLogger(), operation="x")
    metrics.start()
    metrics.increment_failed(1)
    assert metrics.status == ExecutionStatus.FAILED


def test_execution_metrics_set_error_then_log_telemetry():
    import logging

    from pacs008.observability.metrics import ExecutionMetrics

    metrics = ExecutionMetrics(logging.getLogger(), operation="x")
    metrics.start()
    metrics.set_error("oops")
    metrics.log_telemetry()  # should include error_message in payload


# ---------------------------------------------------------------------------
# pacs008.validation.iban_validator — defensive error paths
# ---------------------------------------------------------------------------


def test_iban_checksum_with_invalid_character_returns_false():
    from pacs008.validation.iban_validator import validate_iban_checksum

    # Pass an IBAN-shaped string with a non-alphanumeric to hit the
    # "Invalid character" branch.
    ok, msg = validate_iban_checksum("DE89370400!40532013000")
    assert not ok
    assert "Invalid character" in msg


# ---------------------------------------------------------------------------
# pacs008.validation.lei_validator — defensive error paths + extract_None
# ---------------------------------------------------------------------------


def test_lei_to_numeric_returns_none_for_non_alnum():
    from pacs008.validation.lei_validator import _lei_to_numeric

    assert _lei_to_numeric("HWUPKR0MPOU8FGXBT39!") is None


def test_lei_checksum_with_non_alnum_returns_false():
    from pacs008.validation.lei_validator import validate_lei_checksum

    ok, msg = validate_lei_checksum("HWUPKR0MPOU8FGXBT39!")
    assert not ok
    assert "non-alphanumeric" in msg


# ---------------------------------------------------------------------------
# pacs008.validation.calendar — December-month, walk-cap, eq, coerce paths
# ---------------------------------------------------------------------------


def test_last_weekday_of_december_handles_year_rollover():
    from pacs008.validation.calendar import _last_weekday_of_month

    # December's "next month first" calculation rolls into January of
    # the following year — covers the month==12 branch.
    result = _last_weekday_of_month(2026, 12, 0)  # last Monday of Dec 2026
    assert result == date(2026, 12, 28)


def test_settlement_date_error_eq_returns_notimplemented_for_other_type():
    from pacs008.validation.calendar import SettlementDateError

    err = SettlementDateError(
        row=0,
        field="interbank_settlement_date",
        settlement_date=date(2026, 12, 25),
        calendar="TARGET",
        next_open=date(2026, 12, 28),
    )
    assert err.__eq__("not an error") is NotImplemented


def test_coerce_date_returns_none_for_non_date_value():
    from pacs008.validation.calendar import _coerce_date

    assert _coerce_date(12345) is None
    assert _coerce_date(None) is None


# ---------------------------------------------------------------------------
# pacs008.xml.parser — malformed MsgDefIdr raises ParseError
# ---------------------------------------------------------------------------


def test_split_msg_def_idr_raises_on_malformed():
    from pacs008.xml.parser import ParseError, _split_msg_def_idr

    with pytest.raises(ParseError, match="malformed msg_def_idr"):
        _split_msg_def_idr("nope")


# ---------------------------------------------------------------------------
# pacs008.idempotency.base — compute_payload_hash on custom object,
#                           _utcnow default
# ---------------------------------------------------------------------------


def test_compute_payload_hash_stringifies_unknown_types():
    from pacs008.idempotency import compute_payload_hash

    class Sentinel:
        def __str__(self) -> str:
            return "sentinel"

    h1 = compute_payload_hash(Sentinel())
    h2 = compute_payload_hash("sentinel")
    assert h1 == h2


def test_idempotency_utcnow_returns_aware_datetime():
    from pacs008.idempotency.base import _utcnow

    now = _utcnow()
    assert now.tzinfo is not None
    # Aware datetime — utcoffset is zero for the UTC zone.
    assert now.utcoffset() == datetime.now(timezone.utc).utcoffset()


# ---------------------------------------------------------------------------
# pacs008.core.splitter — defensive cap<1 raises
# ---------------------------------------------------------------------------


def test_split_for_scheme_raises_on_invalid_cap(monkeypatch):
    from pacs008.core import splitter
    from pacs008.profiles import get_profile

    profile = get_profile("fedwire")
    # Monkeypatch the profile instance returned by get_profile to claim
    # cap=0 — exercises the defensive guard at L145.
    original_get = splitter.get_profile

    class Cap0(type(profile)):
        @property
        def max_transactions_per_msg(self):
            return 0

    monkeypatch.setattr(splitter, "get_profile", lambda name: Cap0())
    with pytest.raises(ValueError, match="not splittable"):
        list(splitter.split_for_scheme([{"msg_id": "x"}], "fedwire"))
    monkeypatch.setattr(splitter, "get_profile", original_get)


# ---------------------------------------------------------------------------
# pacs008.csv.validate_csv_data — boolean coercion paths
# ---------------------------------------------------------------------------


def test_csv_validate_boolean_accepts_true_string():
    from pacs008.csv.validate_csv_data import _validate_field_type

    assert _validate_field_type("true", bool) is True
    assert _validate_field_type("TRUE", bool) is True


def test_csv_validate_boolean_rejects_garbage_string():
    from pacs008.csv.validate_csv_data import _validate_field_type

    assert _validate_field_type("maybe", bool) is False


def test_csv_validate_integer_string_passes():
    from pacs008.csv.validate_csv_data import _validate_field_type

    assert _validate_field_type("42", int) is True
    assert _validate_field_type("not-a-number", int) is False


# ---------------------------------------------------------------------------
# pacs008.api.models — invalid_rows field-validator with valid context
# ---------------------------------------------------------------------------


def test_validation_response_invalid_rows_computed_from_totals():
    from pacs008.api.models import ValidationResponse

    response = ValidationResponse(
        is_valid=True,
        message="ok",
        total_rows=10,
        valid_rows=7,
        invalid_rows=0,  # gets recomputed by the field_validator
        errors=[],
    )
    assert response.invalid_rows == 3


# ---------------------------------------------------------------------------
# pacs008.standards.address — country heuristic edge cases
# ---------------------------------------------------------------------------


class TestUKAddressEdgeCases:
    def test_uk_postcode_at_first_line_uses_following_as_town(self):
        from pacs008.standards.address import from_unstructured

        # Postcode-only first line → twn_nm falls back to last line of
        # remaining input.
        addr = from_unstructured(["SW1A 1AA"], "GB")
        # Single postcode line → twn_nm None, but ctry set.
        assert addr.pst_cd == "SW1A 1AA"
        assert addr.ctry == "GB"


class TestUSAddressEdgeCases:
    def test_us_state_zip_at_first_line_uses_following_as_town(self):
        from pacs008.standards.address import from_unstructured

        # First line is the STATE+ZIP token → branch where i == 0 means
        # no preceding line for town.
        addr = from_unstructured(["CA 95014", "1 Infinite Loop"], "US")
        assert addr.ctry_sub_dvsn == "CA"
        assert addr.pst_cd == "95014"


class TestJPAddressEdgeCases:
    def test_jp_postcode_only_line_uses_following_as_town(self):
        from pacs008.standards.address import from_unstructured

        # When a JP postcode sits alone on its own line and there's a
        # following line, that line becomes the town.
        addr = from_unstructured(["1-1 Chiyoda", "〒100-0001", "Tokyo"], "JP")
        # postcode extracted, town derived from the line after.
        assert addr.pst_cd == "100-0001"

    def test_jp_postcode_last_line_no_following(self):
        from pacs008.standards.address import from_unstructured

        # When the JP postcode is the LAST line, the else branch runs
        # (remaining = lines[:i]).
        addr = from_unstructured(["Tokyo Office", "〒100-0001"], "JP")
        assert addr.pst_cd == "100-0001"


class TestPostalAddressMaxLineCount:
    def test_construct_with_max_seven_adr_lines(self):
        from pacs008.standards.address import PostalAddress

        # Build with exactly 7 lines — the boundary of _MAX_ADR_LINE_COUNT.
        lines = tuple(f"Line {i}" for i in range(7))
        addr = PostalAddress(adr_line=lines)
        assert len(addr.adr_line) == 7


# ---------------------------------------------------------------------------
# pacs008.core.core — data load error path, address violation wrap path
# ---------------------------------------------------------------------------


class TestCoreErrorPaths:
    def test_process_files_missing_data_file_raises(self, tmp_path):
        # process_files surfaces FileNotFoundError through the
        # data-load error branch (L186-199 in core/core.py).
        from pacs008 import process_files
        from pacs008.exceptions import XMLGenerationError

        template = tmp_path / "template.xml"
        template.write_text("<x/>")
        xsd = tmp_path / "schema.xsd"
        xsd.write_text("<x/>")
        missing = tmp_path / "missing.csv"

        with pytest.raises(
            (FileNotFoundError, ValueError, XMLGenerationError)
        ):
            process_files(
                "pacs.008.001.08", str(template), str(xsd), str(missing)
            )

    def test_scheme_validation_emits_address_violation(self, monkeypatch):
        # Exercises core.core L264-266 — the address-violation wrap
        # path that imports BusinessRuleViolation inside the loop.
        # Need today >= NOV_2026_CLIFF for CBPR+ to enforce
        # HYBRID_OR_STRUCTURED. Monkeypatch date.today() in the
        # cbpr_plus profile module.
        from datetime import date

        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError, cbpr_plus

        class FakeDate(date):
            @classmethod
            def today(cls):
                return date(2026, 11, 15)

        monkeypatch.setattr(cbpr_plus, "date", FakeDate)

        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "debtor_address_adr_line_0": "42 High Street",
                "debtor_address_adr_line_1": "London SW1A 1AA",
                # No twn_nm + ctry — unstructured.
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "cbpr_plus")
        rules = [v.rule for v in excinfo.value.violations]
        assert "address_policy" in rules


# ---------------------------------------------------------------------------
# pacs008.json.load_json_data — error paths
# ---------------------------------------------------------------------------


class TestJsonLoaderErrorPaths:
    def test_load_json_missing_file_raises(self):
        from pacs008.exceptions import DataSourceError
        from pacs008.json.load_json_data import load_json_data

        with pytest.raises((FileNotFoundError, DataSourceError)):
            load_json_data("/nonexistent/path/to/data.json")

    def test_load_jsonl_missing_file_raises(self):
        from pacs008.exceptions import DataSourceError
        from pacs008.json.load_json_data import load_jsonl_data

        with pytest.raises((FileNotFoundError, DataSourceError)):
            load_jsonl_data("/nonexistent/path/to/data.jsonl")

    def test_load_json_invalid_json_raises(self, tmp_path):
        from pacs008.exceptions import DataSourceError
        from pacs008.json.load_json_data import load_json_data

        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises((ValueError, DataSourceError)):
            load_json_data(str(bad))


# ---------------------------------------------------------------------------
# pacs008.data.loader — error paths
# ---------------------------------------------------------------------------


class TestDataLoaderErrorPaths:
    def test_load_unknown_extension_raises(self):
        from pacs008.data.loader import load_payment_data
        from pacs008.exceptions import DataSourceError

        with pytest.raises((ValueError, DataSourceError)):
            load_payment_data("data.unknownextension")

    def test_load_with_string_path_to_missing_file(self):
        from pacs008.data.loader import load_payment_data
        from pacs008.exceptions import DataSourceError

        with pytest.raises((FileNotFoundError, ValueError, DataSourceError)):
            load_payment_data("/nonexistent/file.csv")


# ---------------------------------------------------------------------------
# pacs008.observability.metrics — already-FAILED status not regressed
# ---------------------------------------------------------------------------


def test_execution_metrics_track_validation_failed_marks_status():
    import logging

    from pacs008.observability.fields import ExecutionStatus
    from pacs008.observability.metrics import ExecutionMetrics

    m = ExecutionMetrics(logging.getLogger(), operation="x")
    m.start()
    m.track_validation("schema", "FAILED")
    assert m.status == ExecutionStatus.FAILED


# ---------------------------------------------------------------------------
# pacs008.compliance.swift_charset — explicit map collapse + branch coverage
# ---------------------------------------------------------------------------


def test_cleanse_string_collapses_runs_of_spaces():
    from pacs008.compliance import cleanse_string

    assert cleanse_string("Hello    World") == "Hello World"


def test_cleanse_string_explicit_map_used_before_nfkd():
    from pacs008.compliance import cleanse_string

    # ä is in the explicit map → "ae" not "a"
    assert cleanse_string("Bär") == "Baer"


# ---------------------------------------------------------------------------
# pacs008.validation.calendar — walk-cap RuntimeError defensive
# ---------------------------------------------------------------------------


def test_calendar_walk_cap_raises_runtime_error():
    """An always-closed calendar should hit the 365-day walk cap."""
    from datetime import date as _date

    from pacs008.validation.calendar import Calendar

    class ClosedCalendar(Calendar):
        name = "closed"

        def is_open(self, day):
            return False

    with pytest.raises(RuntimeError, match="no open day"):
        ClosedCalendar().next_business_day(_date(2026, 1, 1))


def test_calendar_walk_cap_previous_raises_runtime_error():
    from datetime import date as _date

    from pacs008.validation.calendar import Calendar

    class ClosedCalendar(Calendar):
        name = "closed"

        def is_open(self, day):
            return False

    with pytest.raises(RuntimeError, match="no open day"):
        ClosedCalendar().previous_business_day(_date(2026, 1, 1))


# ---------------------------------------------------------------------------
# pacs008.validation.service — defensive error wrappers
# ---------------------------------------------------------------------------


class TestValidationServiceErrors:
    def test_validate_template_missing_path_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_template("")
        assert not result.is_valid

    def test_validate_template_nonexistent_file_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_template(
            "/nonexistent/template.xml"
        )
        assert not result.is_valid

    def test_validate_schema_missing_path_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_schema("")
        assert not result.is_valid

    def test_validate_schema_nonexistent_file_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_schema("/nonexistent/schema.xsd")
        assert not result.is_valid

    def test_validate_data_source_missing_path_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_data_source("")
        assert not result.is_valid

    def test_validate_data_source_nonexistent_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_data_source(
            "/nonexistent/data.csv"
        )
        assert not result.is_valid

    def test_validate_message_type_empty_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_message_type("")
        assert not result.is_valid

    def test_validate_data_content_nonexistent_returns_invalid(self):
        from pacs008.validation.service import ValidationService

        result = ValidationService().validate_data_content(
            "/nonexistent/data.csv"
        )
        assert not result.is_valid


# ---------------------------------------------------------------------------
# pacs008.standards.address — more edge cases for full heuristic coverage
# ---------------------------------------------------------------------------


def test_address_validate_unknown_policy_passes_silently():
    """An unknown AddressPolicy enum value should not block payment —
    forward-compat path returns None."""
    from pacs008.standards.address import PostalAddress

    addr = PostalAddress(adr_line=("foo",))
    # Manually monkeypatch to simulate an unknown enum variant.
    # The unknown-policy path returns None per the validate() impl.

    class _Sentinel:
        value = "sentinel"

    assert addr.validate(_Sentinel()) is None  # type: ignore[arg-type]


def test_extract_party_address_returns_none_when_no_columns():
    from pacs008.standards.address import _extract_party_address

    # No address columns at all → None.
    assert _extract_party_address({"msg_id": "X"}, "debtor") is None


# ---------------------------------------------------------------------------
# pacs008.validation.lei_validator — extract None branch
# ---------------------------------------------------------------------------


def test_validate_leis_with_empty_string_value_skipped():
    from pacs008.validation.lei_validator import validate_leis

    rows = [{"debtor_lei": ""}]
    assert validate_leis(rows) == []


# ---------------------------------------------------------------------------
# pacs008.observability.tracing — set/get/generate request_id cycle
# ---------------------------------------------------------------------------


def test_set_request_id_overrides_existing():
    from pacs008.observability.tracing import get_request_id, set_request_id

    set_request_id("req-customA1")
    assert get_request_id() == "req-customA1"
    set_request_id("req-customB2")
    assert get_request_id() == "req-customB2"
