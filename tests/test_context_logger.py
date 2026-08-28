# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""The Context singleton's logger and log-level branches.

`Context` is a singleton, which makes it awkward to test and easy to leave
untested — every case has to reset the class attribute or the second test in a
file inherits whatever the first one built. That is why these branches were the
least-covered in the package rather than because they are unimportant: the log
level decides whether anything is recorded at all when a batch run goes wrong.

The fixture resets `Context.instance` around each test, so the order they run in
cannot change the result.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from pacs008.context.context import Context


@pytest.fixture(autouse=True)
def fresh_singleton() -> Iterator[None]:
    """Give each test its own Context, and give the next test a clean one."""
    previous = Context.instance
    Context.instance = None
    yield
    Context.instance = previous


class TestSingleton:
    def test_get_instance_creates_one_and_returns_it_again(self) -> None:
        first = Context.get_instance()
        assert Context.get_instance() is first

    def test_constructing_a_second_one_is_refused(self) -> None:
        Context.get_instance()
        with pytest.raises(RuntimeError, match="singleton"):
            Context()


class TestLogLevel:
    """Accepted as a name or a number, refused otherwise."""

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("debug", logging.DEBUG),
            ("  Warning  ", logging.WARNING),
            ("CRITICAL", logging.CRITICAL),
            (logging.ERROR, logging.ERROR),
        ],
    )
    def test_valid_levels_are_accepted(
        self, given: object, expected: int
    ) -> None:
        context = Context.get_instance()
        context.set_log_level(given)  # type: ignore[arg-type]
        assert context.log_level == expected

    @pytest.mark.parametrize("given", ["LOUD", "", 999])
    def test_invalid_levels_are_refused(self, given: object) -> None:
        context = Context.get_instance()
        with pytest.raises(ValueError, match="Invalid log level"):
            context.set_log_level(given)  # type: ignore[arg-type]


class TestInitLogger:
    def test_the_logger_is_built_and_configured(self) -> None:
        context = Context.get_instance()
        context.logger = None  # type: ignore[assignment]

        context.init_logger()

        assert isinstance(context.logger, logging.Logger)
        assert context.logger.level == context.log_level
        assert context.logger.handlers

    def test_initialising_twice_is_refused(self) -> None:
        context = Context.get_instance()
        context.logger = None  # type: ignore[assignment]
        context.init_logger()

        # Guarded rather than idempotent on purpose: a second call would attach
        # a second handler and every line would be logged twice.
        with pytest.raises(RuntimeError, match="already been initialized"):
            context.init_logger()

    def test_get_logger_initialises_on_demand(self) -> None:
        context = Context.get_instance()
        context.logger = None  # type: ignore[assignment]

        assert isinstance(context.get_logger(), logging.Logger)
