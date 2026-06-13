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

"""Tests for pacs008.validation.calendar."""

from __future__ import annotations

from datetime import date

import pytest

from pacs008.profiles import CBPRPlusProfile, FedwireProfile, GenericProfile
from pacs008.validation.calendar import (
    AlwaysOpenCalendar,
    CHAPSCalendar,
    FedwireCalendar,
    SettlementDateError,
    TARGETCalendar,
    compute_easter,
    get_calendar,
    list_calendars,
    validate_settlement_dates,
)


# ---------------------------------------------------------------------------
# Easter — known dates from ECB calendar
# ---------------------------------------------------------------------------


class TestEaster:
    @pytest.mark.parametrize(
        "year,expected",
        [
            (2024, date(2024, 3, 31)),
            (2025, date(2025, 4, 20)),
            (2026, date(2026, 4, 5)),
            (2027, date(2027, 3, 28)),
            (2028, date(2028, 4, 16)),
            (2029, date(2029, 4, 1)),
            (2030, date(2030, 4, 21)),
        ],
    )
    def test_known_easter_sundays(self, year, expected):
        assert compute_easter(year) == expected


# ---------------------------------------------------------------------------
# AlwaysOpenCalendar — sanity (FedNow, SCT Inst)
# ---------------------------------------------------------------------------


class TestAlwaysOpen:
    def setup_method(self):
        self.cal = AlwaysOpenCalendar()

    def test_open_every_day(self):
        for d in (date(2026, 1, 1), date(2026, 12, 25), date(2026, 6, 14)):
            assert self.cal.is_open(d)

    def test_next_business_day_is_just_tomorrow(self):
        assert (
            self.cal.next_business_day(date(2026, 12, 25))
            == date(2026, 12, 26)
        )


# ---------------------------------------------------------------------------
# TARGETCalendar
# ---------------------------------------------------------------------------


class TestTARGET:
    def setup_method(self):
        self.cal = TARGETCalendar()

    def test_weekends_closed(self):
        # 13 June 2026 is a Saturday
        assert self.cal.is_closed(date(2026, 6, 13))
        # 14 June 2026 is a Sunday
        assert self.cal.is_closed(date(2026, 6, 14))

    @pytest.mark.parametrize(
        "d,label",
        [
            (date(2026, 1, 1), "New Year"),
            (date(2026, 5, 1), "Labour Day"),
            (date(2026, 12, 25), "Christmas"),
            (date(2026, 12, 26), "Boxing"),
            (date(2026, 4, 3), "Good Friday 2026"),
            (date(2026, 4, 6), "Easter Monday 2026"),
            (date(2027, 3, 26), "Good Friday 2027"),
            (date(2027, 3, 29), "Easter Monday 2027"),
        ],
    )
    def test_fixed_and_movable_holidays_closed(self, d, label):
        assert self.cal.is_closed(d), f"TARGET should be closed on {label}"

    def test_ordinary_weekday_open(self):
        # 15 June 2026 — a Monday — open
        assert self.cal.is_open(date(2026, 6, 15))

    def test_next_business_day_skips_year_end(self):
        # 25 Dec 2026 = Fri (closed), 26 = Sat / St Stephen (closed),
        # 27 = Sun (closed), 28 = Mon → open. TARGET does NOT shift
        # holiday observance to Monday the way CHAPS does.
        assert (
            self.cal.next_business_day(date(2026, 12, 25))
            == date(2026, 12, 28)
        )

    def test_next_business_day_skips_easter(self):
        # 3 Apr 2026 (Good Friday). Next: Tue 7 Apr 2026 (after Easter
        # Monday + weekend).
        assert (
            self.cal.next_business_day(date(2026, 4, 3))
            == date(2026, 4, 7)
        )


# ---------------------------------------------------------------------------
# FedwireCalendar
# ---------------------------------------------------------------------------


class TestFedwire:
    def setup_method(self):
        self.cal = FedwireCalendar()

    @pytest.mark.parametrize(
        "d,label",
        [
            (date(2026, 1, 1), "New Year"),
            (date(2026, 1, 19), "MLK Day"),
            (date(2026, 2, 16), "Presidents' Day"),
            (date(2026, 5, 25), "Memorial Day"),
            (date(2026, 6, 19), "Juneteenth"),
            (date(2026, 7, 4), "Independence Day (Sat falling Fri-OK)"),
            (date(2026, 9, 7), "Labor Day"),
            (date(2026, 10, 12), "Columbus Day"),
            (date(2026, 11, 11), "Veterans Day"),
            (date(2026, 11, 26), "Thanksgiving"),
            (date(2026, 12, 25), "Christmas"),
        ],
    )
    def test_federal_holidays_closed(self, d, label):
        # Weekend holidays might still be "open" Mon — but for those
        # that fall on weekdays this should always close.
        if d.weekday() < 5:
            assert self.cal.is_closed(d), f"Fedwire closed on {label}"

    def test_juneteenth_open_before_2021(self):
        # Pre-2021, Juneteenth wasn't a federal holiday.
        # 19 June 2020 was a Friday — Fedwire was open.
        assert self.cal.is_open(date(2020, 6, 19))

    def test_juneteenth_closed_from_2021(self):
        # 19 June 2023 = Mon, closed.
        assert self.cal.is_closed(date(2023, 6, 19))

    def test_sunday_holiday_observed_on_monday(self):
        # 4 July 2027 = Sunday; observed Monday 5 July.
        assert self.cal.is_closed(date(2027, 7, 5))

    def test_saturday_holiday_no_friday_observance(self):
        # 4 July 2026 = Saturday; the preceding Friday (3 July 2026)
        # is OPEN for Fedwire.
        assert self.cal.is_open(date(2026, 7, 3))

    def test_ordinary_weekday_open(self):
        # 15 June 2026 — a Monday — open
        assert self.cal.is_open(date(2026, 6, 15))

    def test_weekend_closed(self):
        assert self.cal.is_closed(date(2026, 6, 13))  # Sat
        assert self.cal.is_closed(date(2026, 6, 14))  # Sun


# ---------------------------------------------------------------------------
# CHAPSCalendar — including the gnarly weekend substitution rule
# ---------------------------------------------------------------------------


class TestCHAPS:
    def setup_method(self):
        self.cal = CHAPSCalendar()

    def test_weekends_closed(self):
        assert self.cal.is_closed(date(2026, 6, 13))
        assert self.cal.is_closed(date(2026, 6, 14))

    @pytest.mark.parametrize(
        "d,label",
        [
            (date(2026, 1, 1), "New Year"),
            (date(2026, 5, 4), "Early May Bank Holiday (1st Mon May)"),
            (date(2026, 5, 25), "Spring Bank Holiday (last Mon May)"),
            (date(2026, 8, 31), "Summer Bank Holiday (last Mon Aug)"),
            (date(2026, 12, 25), "Christmas"),
            (date(2026, 12, 28), "Boxing Day observed (26 Dec = Sat)"),
            (date(2026, 4, 3), "Good Friday 2026"),
            (date(2026, 4, 6), "Easter Monday 2026"),
        ],
    )
    def test_uk_bank_holidays_closed(self, d, label):
        assert self.cal.is_closed(d), f"CHAPS closed on {label}"

    def test_christmas_substitution_2027(self):
        # 25 Dec 2027 = Saturday — observed Monday 27 Dec.
        # 26 Dec 2027 = Sunday — observed Tuesday 28 Dec.
        # 29 Dec 2027 = Wednesday — open.
        assert self.cal.is_closed(date(2027, 12, 25))  # Sat
        assert self.cal.is_closed(date(2027, 12, 26))  # Sun
        assert self.cal.is_closed(date(2027, 12, 27))  # Mon (xmas obs)
        assert self.cal.is_closed(date(2027, 12, 28))  # Tue (boxing obs)
        assert self.cal.is_open(date(2027, 12, 29))   # Wed

    def test_new_year_substitution_2028(self):
        # 1 Jan 2028 = Saturday → observed Monday 3 Jan.
        assert self.cal.is_closed(date(2028, 1, 1))
        assert self.cal.is_closed(date(2028, 1, 3))

    def test_next_business_day_skips_easter(self):
        assert (
            self.cal.next_business_day(date(2026, 4, 3))
            == date(2026, 4, 7)
        )

    def test_ordinary_weekday_open(self):
        # Mon 15 June 2026 — not a holiday
        assert self.cal.is_open(date(2026, 6, 15))


# ---------------------------------------------------------------------------
# previous_business_day
# ---------------------------------------------------------------------------


class TestPreviousBusinessDay:
    def test_target_previous_skips_christmas(self):
        cal = TARGETCalendar()
        # 27 Dec 2026 is a Sunday. Previous: Thu 24 Dec (25/26 closed).
        assert (
            cal.previous_business_day(date(2026, 12, 28))
            == date(2026, 12, 24)
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_list_includes_known_calendars(self):
        names = list_calendars()
        assert "always_open" in names
        assert "target" in names
        assert "fedwire" in names
        assert "chaps" in names

    def test_target2_alias(self):
        assert isinstance(get_calendar("target2"), TARGETCalendar)

    def test_case_insensitive(self):
        assert isinstance(get_calendar("FEDWIRE"), FedwireCalendar)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown calendar"):
            get_calendar("not_a_calendar")


# ---------------------------------------------------------------------------
# Profile.calendar wiring
# ---------------------------------------------------------------------------


class TestProfileCalendar:
    def test_generic_is_always_open(self):
        assert isinstance(GenericProfile().calendar, AlwaysOpenCalendar)

    def test_cbpr_plus_is_target(self):
        assert isinstance(CBPRPlusProfile().calendar, TARGETCalendar)

    def test_fedwire_is_fedwire(self):
        assert isinstance(FedwireProfile().calendar, FedwireCalendar)


# ---------------------------------------------------------------------------
# validate_settlement_dates pipeline helper
# ---------------------------------------------------------------------------


class TestValidateSettlementDates:
    def test_empty_returns_empty(self):
        assert (
            validate_settlement_dates([], TARGETCalendar()) == []
        )

    def test_open_date_passes(self):
        rows = [{"interbank_settlement_date": "2026-06-15"}]  # Mon
        assert validate_settlement_dates(rows, TARGETCalendar()) == []

    def test_closed_date_flagged_with_next_open(self):
        rows = [{"interbank_settlement_date": "2026-12-25"}]
        errs = validate_settlement_dates(rows, TARGETCalendar())
        assert len(errs) == 1
        err = errs[0]
        assert err.row == 0
        assert err.settlement_date == date(2026, 12, 25)
        assert err.calendar == "TARGET"
        # Mon 28 Dec 2026 — TARGET does not shift holiday observance
        # to Monday, so the next open day after Christmas-week
        # closings is the Mon directly after the weekend.
        assert err.next_open == date(2026, 12, 28)
        assert "2026-12-25" in err.message
        assert "2026-12-28" in err.message

    def test_missing_field_skipped(self):
        rows = [{"msg_id": "X"}]
        assert validate_settlement_dates(rows, TARGETCalendar()) == []

    def test_empty_string_skipped(self):
        rows = [{"interbank_settlement_date": ""}]
        assert validate_settlement_dates(rows, TARGETCalendar()) == []

    def test_unparseable_date_skipped(self):
        rows = [{"interbank_settlement_date": "not-a-date"}]
        assert validate_settlement_dates(rows, TARGETCalendar()) == []

    def test_native_date_accepted(self):
        rows = [{"interbank_settlement_date": date(2026, 12, 25)}]
        errs = validate_settlement_dates(rows, TARGETCalendar())
        assert len(errs) == 1

    def test_custom_field_name(self):
        rows = [{"sttlm_dt": "2026-12-25"}]
        errs = validate_settlement_dates(
            rows, TARGETCalendar(), field_name="sttlm_dt"
        )
        assert len(errs) == 1

    def test_always_open_never_flags(self):
        rows = [
            {"interbank_settlement_date": "2026-12-25"},
            {"interbank_settlement_date": "2026-01-01"},
        ]
        assert validate_settlement_dates(rows, AlwaysOpenCalendar()) == []

    def test_multiple_rows_aggregated(self):
        rows = [
            {"interbank_settlement_date": "2026-06-15"},  # ok
            {"interbank_settlement_date": "2026-12-25"},  # closed
            {"interbank_settlement_date": "2026-12-26"},  # closed
        ]
        errs = validate_settlement_dates(rows, TARGETCalendar())
        assert sorted(e.row for e in errs) == [1, 2]


# ---------------------------------------------------------------------------
# SettlementDateError dataclass surface
# ---------------------------------------------------------------------------


class TestSettlementDateError:
    def test_equality_and_repr(self):
        a = SettlementDateError(
            row=0,
            field="interbank_settlement_date",
            settlement_date=date(2026, 12, 25),
            calendar="TARGET",
            next_open=date(2026, 12, 29),
        )
        b = SettlementDateError(
            row=0,
            field="interbank_settlement_date",
            settlement_date=date(2026, 12, 25),
            calendar="TARGET",
            next_open=date(2026, 12, 29),
        )
        assert a == b
        assert "TARGET" in repr(a)


# ---------------------------------------------------------------------------
# Integration through _run_scheme_validation
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_cbpr_plus_blocks_christmas_settlement(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "interbank_settlement_date": "2026-12-25",
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "cbpr_plus")
        assert any(
            v.rule == "settlement_date_closed"
            for v in excinfo.value.violations
        )

    def test_fedwire_blocks_thanksgiving_settlement(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "interbank_settlement_date": "2026-11-26",  # Thanksgiving
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "fedwire")
        assert any(
            v.rule == "settlement_date_closed"
            for v in excinfo.value.violations
        )

    def test_generic_does_not_block_any_date(self):
        from pacs008.core.core import _run_scheme_validation

        rows = [
            {
                "msg_id": "X",
                "interbank_settlement_date": "2026-12-25",
            }
        ]
        # No exception — generic uses AlwaysOpenCalendar.
        _run_scheme_validation(rows, "generic")
