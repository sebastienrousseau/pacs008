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

"""Settlement-date calendars for the major payment rails.

A pacs.008 message with an ``IntrBkSttlmDt`` on a rail's closing day is
rejected at settlement (or held until the next business day, depending
on the rail). This module gives every scheme profile a calendar so the
pacs008 validation pipeline can flag those rejections **before** the
message leaves the institution.

Rules are encoded computationally rather than as baked date lists so
they remain correct for any future year. Easter is computed using the
anonymous Gregorian (Butcher) algorithm.

Shipped calendars:

- :class:`AlwaysOpenCalendar` — for 24/7 rails (FedNow, EPC SCT Inst).
- :class:`TARGETCalendar` — ECB's TARGET2 / T2 RTGS closing days:
  1 January, Good Friday, Easter Monday, 1 May, 25 December,
  26 December, plus all weekends.
- :class:`FedwireCalendar` — the 11 Federal Reserve holidays
  (incl. Juneteenth from 2021), with Sunday → Monday substitution.
- :class:`CHAPSCalendar` — Bank of England / England & Wales bank
  holidays, with weekend-to-next-weekday substitution for the fixed
  dates.

The :func:`get_calendar` factory accepts a scheme profile name or a
calendar name directly.

References:

- ECB — *TARGET 2 calendar 2024-2028*.
- Federal Reserve — *Federal Reserve Bank Holiday Schedule*.
- Bank of England — *CHAPS operating days*.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

__all__ = [
    "AlwaysOpenCalendar",
    "CHAPSCalendar",
    "Calendar",
    "FedwireCalendar",
    "SettlementDateError",
    "TARGETCalendar",
    "compute_easter",
    "get_calendar",
    "list_calendars",
    "register_calendar",
    "validate_settlement_dates",
]


# Cap on the number of days next_business_day / previous_business_day
# will walk before giving up. A real calendar should never have a 365-day
# gap; the cap exists to surface broken implementations rather than spin
# forever.
_WALK_CAP = 365


# ---------------------------------------------------------------------------
# Easter computation (anonymous Gregorian / Butcher algorithm)
# ---------------------------------------------------------------------------


def compute_easter(year: int) -> date:
    """Return the Western (Gregorian) Easter Sunday date for ``year``.

    Uses the anonymous Gregorian algorithm (also known as the Butcher
    algorithm). Valid for the Gregorian calendar (1583 onwards).

    Args:
        year: Four-digit year.

    Returns:
        The Easter Sunday ``date`` for that year.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    month = (h + el - 7 * m + 114) // 31
    day = ((h + el - 7 * m + 114) % 31) + 1
    return date(year, month, day)


# ---------------------------------------------------------------------------
# Floating-holiday helpers
# ---------------------------------------------------------------------------


def _nth_weekday_of_month(
    year: int, month: int, weekday: int, n: int
) -> date:
    """Return the n-th ``weekday`` (Mon=0..Sun=6) of ``month`` in ``year``."""
    first = date(year, month, 1)
    delta = (weekday - first.weekday()) % 7
    return first + timedelta(days=delta + 7 * (n - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the last ``weekday`` (Mon=0..Sun=6) of ``month`` in ``year``."""
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    delta = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=delta)


# ---------------------------------------------------------------------------
# Calendar ABC + walk helpers
# ---------------------------------------------------------------------------


class Calendar(ABC):
    """Abstract settlement calendar."""

    name: str

    @abstractmethod
    def is_open(self, day: date) -> bool:
        """Return True iff settlement is permitted on ``day``."""

    def is_closed(self, day: date) -> bool:
        """Convenience inverse of :meth:`is_open`."""
        return not self.is_open(day)

    def next_business_day(self, day: date) -> date:
        """Return the first open date strictly after ``day``."""
        candidate = day + timedelta(days=1)
        for _ in range(_WALK_CAP):
            if self.is_open(candidate):
                return candidate
            candidate += timedelta(days=1)
        raise RuntimeError(
            f"Calendar {self.name!r}: no open day within {_WALK_CAP} days "
            f"of {day.isoformat()}"
        )

    def previous_business_day(self, day: date) -> date:
        """Return the first open date strictly before ``day``."""
        candidate = day - timedelta(days=1)
        for _ in range(_WALK_CAP):
            if self.is_open(candidate):
                return candidate
            candidate -= timedelta(days=1)
        raise RuntimeError(
            f"Calendar {self.name!r}: no open day within {_WALK_CAP} days "
            f"before {day.isoformat()}"
        )


# ---------------------------------------------------------------------------
# Concrete calendars
# ---------------------------------------------------------------------------


class AlwaysOpenCalendar(Calendar):
    """24/7 calendar — for FedNow, EPC SCT Inst and similar instant rails."""

    name = "always_open"

    def is_open(self, day: date) -> bool:
        return True


class TARGETCalendar(Calendar):
    """ECB TARGET2 / T2 RTGS closing days.

    Closed days:

    - All Saturdays and Sundays
    - 1 January (New Year's Day)
    - Good Friday
    - Easter Monday
    - 1 May (Labour Day)
    - 25 December (Christmas Day)
    - 26 December (Boxing / St Stephen's Day)
    """

    name = "TARGET"

    _FIXED_HOLIDAYS: frozenset[tuple[int, int]] = frozenset(
        {(1, 1), (5, 1), (12, 25), (12, 26)}
    )

    def is_open(self, day: date) -> bool:
        # Weekends
        if day.weekday() >= 5:
            return False
        # Fixed holidays
        if (day.month, day.day) in self._FIXED_HOLIDAYS:
            return False
        # Movable holidays around Easter
        easter = compute_easter(day.year)
        if day == easter - timedelta(days=2):
            return False
        if day == easter + timedelta(days=1):
            return False
        return True


class FedwireCalendar(Calendar):
    """US Federal Reserve / Fedwire ISO 20022 operating-day calendar.

    Closed days:

    - All Saturdays and Sundays
    - New Year's Day (1 January) — Sunday observed Monday
    - Martin Luther King Jr. Day — 3rd Monday in January
    - Washington's Birthday / Presidents' Day — 3rd Monday in February
    - Memorial Day — last Monday in May
    - Juneteenth (19 June) — Federal holiday from 2021
    - Independence Day (4 July) — Sunday observed Monday
    - Labor Day — 1st Monday in September
    - Columbus Day — 2nd Monday in October
    - Veterans Day (11 November) — Sunday observed Monday
    - Thanksgiving Day — 4th Thursday in November
    - Christmas Day (25 December) — Sunday observed Monday

    Substitution: when a fixed holiday falls on a Sunday, Fedwire is
    closed on the following Monday. Saturday-falling holidays do NOT
    trigger a Friday observance (Fedwire is open the Friday before).
    """

    name = "Fedwire"

    _FIXED_HOLIDAYS: tuple[tuple[int, int], ...] = (
        (1, 1),    # New Year's Day
        (6, 19),   # Juneteenth (from 2021)
        (7, 4),    # Independence Day
        (11, 11),  # Veterans Day
        (12, 25),  # Christmas Day
    )

    _JUNETEENTH_FIRST_YEAR = 2021

    def is_open(self, day: date) -> bool:
        if day.weekday() >= 5:
            return False

        # Check fixed holidays (with Sunday-on-Monday substitution).
        for month, dom in self._FIXED_HOLIDAYS:
            if (
                month == 6
                and dom == 19
                and day.year < self._JUNETEENTH_FIRST_YEAR
            ):
                continue
            holiday = date(day.year, month, dom)
            if day == holiday and holiday.weekday() < 5:
                return False
            # Substitute: when holiday falls on Sunday, observe Monday.
            if (
                holiday.weekday() == 6
                and day == holiday + timedelta(days=1)
            ):
                return False

        # Floating holidays.
        if day == _nth_weekday_of_month(day.year, 1, 0, 3):  # MLK Day
            return False
        if day == _nth_weekday_of_month(day.year, 2, 0, 3):  # Presidents'
            return False
        if day == _last_weekday_of_month(day.year, 5, 0):  # Memorial Day
            return False
        if day == _nth_weekday_of_month(day.year, 9, 0, 1):  # Labor Day
            return False
        if day == _nth_weekday_of_month(day.year, 10, 0, 2):  # Columbus
            return False
        if day == _nth_weekday_of_month(day.year, 11, 3, 4):  # Thanksgiving
            return False

        return True


class CHAPSCalendar(Calendar):
    """Bank of England CHAPS operating-day calendar (England & Wales).

    Closed days:

    - All Saturdays and Sundays
    - New Year's Day (1 January) — weekend observed next weekday
    - Good Friday
    - Easter Monday
    - Early May Bank Holiday — 1st Monday in May
    - Spring Bank Holiday — last Monday in May
    - Summer Bank Holiday — last Monday in August (England)
    - Christmas Day (25 December) — weekend observed next weekday
    - Boxing Day (26 December) — weekend observed next weekday

    UK substitution rule: when a fixed holiday falls on Saturday or
    Sunday, the next available weekday is observed. If Christmas Day
    is a Saturday, Monday is observed for Christmas and Tuesday for
    Boxing Day (Boxing Day proper falls on Sunday and bumps to
    Tuesday).
    """

    name = "CHAPS"

    _FIXED_HOLIDAYS: tuple[tuple[int, int], ...] = (
        (1, 1),
        (12, 25),
        (12, 26),
    )

    def is_open(self, day: date) -> bool:
        if day.weekday() >= 5:
            return False

        # Fixed holidays with weekend substitution.
        substituted_days = self._substituted_fixed_holidays(day.year)
        if day in substituted_days:
            return False

        # Easter-driven.
        easter = compute_easter(day.year)
        if day == easter - timedelta(days=2):  # Good Friday
            return False
        if day == easter + timedelta(days=1):  # Easter Monday
            return False

        # Floating Mondays.
        if day == _nth_weekday_of_month(day.year, 5, 0, 1):  # Early May
            return False
        if day == _last_weekday_of_month(day.year, 5, 0):  # Spring Bank
            return False
        if day == _last_weekday_of_month(day.year, 8, 0):  # Summer Bank
            return False

        return True

    def _substituted_fixed_holidays(self, year: int) -> set[date]:
        """Return the set of observed dates for the year's fixed holidays.

        For each (month, dom) holiday, picks the next weekday on or
        after the calendar date — skipping over preceding substitutions
        so e.g. Boxing Day always observes after Christmas Day.
        """
        observed: list[date] = []
        for month, dom in self._FIXED_HOLIDAYS:
            candidate = date(year, month, dom)
            while (
                candidate.weekday() >= 5
                or candidate in observed
            ):
                candidate += timedelta(days=1)
            observed.append(candidate)
        return set(observed)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_CALENDARS: dict[str, type[Calendar]] = {}


def register_calendar(name: str, calendar_cls: type[Calendar]) -> None:
    """Register a calendar under a lookup name (case-insensitive)."""
    _CALENDARS[name.lower()] = calendar_cls


def get_calendar(name: str) -> Calendar:
    """Look up a calendar by name (case-insensitive).

    Raises:
        ValueError: if no calendar is registered under ``name``.
    """
    key = name.lower()
    if key not in _CALENDARS:
        raise ValueError(
            f"Unknown calendar {name!r}; available: "
            f"{sorted(_CALENDARS)}"
        )
    return _CALENDARS[key]()


def list_calendars() -> list[str]:
    """Return registered calendar names, sorted."""
    return sorted(_CALENDARS)


register_calendar("always_open", AlwaysOpenCalendar)
register_calendar("target", TARGETCalendar)
register_calendar("target2", TARGETCalendar)
register_calendar("fedwire", FedwireCalendar)
register_calendar("chaps", CHAPSCalendar)


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------


class SettlementDateError:
    """A single settlement-date validation finding."""

    __slots__ = ("row", "field", "settlement_date", "calendar", "next_open")

    def __init__(
        self,
        row: int,
        field: str,
        settlement_date: date,
        calendar: str,
        next_open: date,
    ) -> None:
        self.row = row
        self.field = field
        self.settlement_date = settlement_date
        self.calendar = calendar
        self.next_open = next_open

    @property
    def message(self) -> str:
        return (
            f"settlement date {self.settlement_date.isoformat()} is a "
            f"closing day on the {self.calendar} calendar; next open day "
            f"is {self.next_open.isoformat()}"
        )

    def __repr__(self) -> str:
        return (
            f"SettlementDateError(row={self.row}, "
            f"settlement_date={self.settlement_date.isoformat()!r}, "
            f"calendar={self.calendar!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SettlementDateError):
            return NotImplemented
        return (
            self.row == other.row
            and self.field == other.field
            and self.settlement_date == other.settlement_date
            and self.calendar == other.calendar
            and self.next_open == other.next_open
        )


def validate_settlement_dates(
    payment_data: list[dict[str, object]],
    calendar: Calendar,
    field_name: str = "interbank_settlement_date",
) -> list[SettlementDateError]:
    """Flag rows whose settlement date is a closing day for ``calendar``.

    Args:
        payment_data: Payment-row dicts.
        calendar: Calendar to validate against (typically obtained from
            ``profile.calendar`` for a scheme).
        field_name: Column name carrying the ISO-format settlement date.
            Defaults to ``"interbank_settlement_date"``.

    Returns:
        List of :class:`SettlementDateError`. Rows without a settlement
        date column or with an empty/unparseable value are skipped
        silently — the canonical CSV validator is responsible for the
        "required field missing" path.
    """
    errors: list[SettlementDateError] = []

    for row_idx, row in enumerate(payment_data):
        raw = row.get(field_name)
        if raw in (None, ""):
            continue

        settlement_date = _coerce_date(raw)
        if settlement_date is None:
            continue

        if calendar.is_open(settlement_date):
            continue

        errors.append(
            SettlementDateError(
                row=row_idx,
                field=field_name,
                settlement_date=settlement_date,
                calendar=calendar.name,
                next_open=calendar.next_business_day(settlement_date),
            )
        )

    return errors


def _coerce_date(value: object) -> Optional[date]:
    """Best-effort conversion to ``date`` — returns ``None`` if unparseable."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
