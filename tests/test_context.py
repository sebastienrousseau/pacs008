"""Tests for the Context singleton class."""

import logging

import pytest

from pacs008.context.context import Context


@pytest.fixture(autouse=True)
def reset_context():
    """Reset Context singleton before each test."""
    Context.instance = None
    yield
    Context.instance = None


class TestContext:
    def test_get_instance_creates_singleton(self):
        ctx = Context.get_instance()
        assert ctx is not None
        assert Context.instance is ctx

    def test_get_instance_returns_same(self):
        ctx1 = Context.get_instance()
        ctx2 = Context.get_instance()
        assert ctx1 is ctx2

    def test_double_init_raises(self):
        Context()
        with pytest.raises(RuntimeError, match="singleton"):
            Context()

    def test_get_logger(self):
        ctx = Context.get_instance()
        logger = ctx.get_logger()
        assert isinstance(logger, logging.Logger)

    def test_set_name(self):
        ctx = Context.get_instance()
        ctx.set_name("test_app")
        assert ctx.name == "test_app"

    def test_set_log_level_int(self):
        ctx = Context.get_instance()
        ctx.set_log_level(logging.DEBUG)
        assert ctx.log_level == logging.DEBUG
        assert ctx.logger.level == logging.DEBUG

    def test_set_log_level_string(self):
        ctx = Context.get_instance()
        ctx.set_log_level("WARNING")
        assert ctx.log_level == logging.WARNING

    def test_set_log_level_string_case_insensitive(self):
        ctx = Context.get_instance()
        ctx.set_log_level("  debug  ")
        assert ctx.log_level == logging.DEBUG

    def test_set_invalid_log_level_int(self):
        ctx = Context.get_instance()
        with pytest.raises(ValueError, match="Invalid log level"):
            ctx.set_log_level(999)

    def test_set_invalid_log_level_string(self):
        ctx = Context.get_instance()
        with pytest.raises(ValueError, match="Invalid log level"):
            ctx.set_log_level("INVALID")

    def test_init_logger_raises_if_already_initialized(self):
        ctx = Context.get_instance()
        # Logger is already initialized in __init__
        with pytest.raises(RuntimeError, match="already been initialized"):
            ctx.init_logger()
