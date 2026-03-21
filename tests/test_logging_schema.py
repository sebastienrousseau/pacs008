"""Tests for the structured logging schema module."""

import json
import logging
import os
import tempfile
import time

import pytest

from pacs008.logging_schema import (
    Events,
    ExecutionMetrics,
    ExecutionStatus,
    ExecutionSummaryTracker,
    Fields,
    JSONFormatter,
    LogLevel,
    _redact_pii_from_dict,
    _sanitize_value,
    configure_json_logging,
    generate_request_id,
    get_request_id,
    log_data_load_event,
    log_event,
    log_process_error,
    log_process_start,
    log_process_success,
    log_validation_event,
    log_xml_generation_event,
    mask_sensitive_data,
    set_request_id,
)


class TestMaskSensitiveData:
    """Test PII masking."""

    def test_long_value_masked(self):
        result = mask_sensitive_data("GB29NWBK60161331926819", 4)
        assert result == "GB29**************6819"

    def test_short_value_fully_masked(self):
        result = mask_sensitive_data("Short", 4)
        assert result == "****"

    def test_exact_boundary(self):
        result = mask_sensitive_data("12345678", 4)
        assert result == "****"

    def test_visible_chars_default(self):
        result = mask_sensitive_data("ABCDEFGHIJKLMNOP")
        assert result.startswith("ABCD")
        assert result.endswith("MNOP")
        assert "****" in result


class TestSanitizeValue:
    """Test log injection prevention."""

    def test_removes_newlines(self):
        assert _sanitize_value("hello\nworld") == "helloworld"

    def test_removes_carriage_return(self):
        assert _sanitize_value("hello\rworld") == "helloworld"

    def test_non_string_passthrough(self):
        assert _sanitize_value(42) == 42
        assert _sanitize_value(None) is None

    def test_clean_string_unchanged(self):
        assert _sanitize_value("clean") == "clean"


class TestRedactPiiFromDict:
    """Test PII redaction for GDPR/PCI-DSS compliance."""

    def test_redacts_iban(self):
        result = _redact_pii_from_dict({"debtor_iban": "GB29NWBK60161331926819"})
        assert "GB29" in result["debtor_iban"]
        assert "****" in result["debtor_iban"] or "*" in result["debtor_iban"]

    def test_redacts_bic(self):
        result = _redact_pii_from_dict({"creditor_bic": "DEUTDEFF"})
        assert result["creditor_bic"] == "DEUT**FF"

    def test_redacts_short_bic(self):
        result = _redact_pii_from_dict({"bic": "SHORT"})
        assert result["bic"] == "****"

    def test_redacts_name(self):
        result = _redact_pii_from_dict({"debtor_name": "John Doe"})
        assert result["debtor_name"] == "[REDACTED]"

    def test_redacts_account(self):
        result = _redact_pii_from_dict({"account_number": "1234567890"})
        assert result["account_number"] != "1234567890"  # value is masked
        assert result["account_number"].startswith("1234")

    def test_non_pii_unchanged(self):
        result = _redact_pii_from_dict({"msg_id": "MSG-001", "amount": 1000})
        assert result["msg_id"] == "MSG-001"
        assert result["amount"] == 1000

    def test_nested_dict_redacted(self):
        result = _redact_pii_from_dict({"debtor": {"name": "John Doe"}})
        assert result["debtor"]["name"] == "[REDACTED]"

    def test_list_of_dicts_redacted(self):
        result = _redact_pii_from_dict(
            {"transactions": [{"debtor_name": "Alice"}]}
        )
        assert result["transactions"][0]["debtor_name"] == "[REDACTED]"

    def test_list_of_non_dicts(self):
        result = _redact_pii_from_dict({"tags": ["a\nb", "c"]})
        assert result["tags"] == ["ab", "c"]

    def test_sanitizes_newlines_in_iban(self):
        result = _redact_pii_from_dict({"iban": "GB29\nNWBK60161331926819"})
        assert "\n" not in result["iban"]


class TestRequestId:
    """Test request ID generation and context management."""

    def test_generate_request_id_format(self):
        rid = generate_request_id()
        assert rid.startswith("req-")
        assert len(rid) == 12  # "req-" + 8 hex chars

    def test_set_and_get_request_id(self):
        set_request_id("req-test1234")
        assert get_request_id() == "req-test1234"

    def test_get_auto_generates_if_none(self):
        set_request_id(None)
        rid = get_request_id()
        assert rid.startswith("req-")


class TestLogEvent:
    """Test structured log_event function."""

    def test_log_event_produces_json(self, caplog):
        logger = logging.getLogger("test_log_event")
        with caplog.at_level(logging.INFO, logger="test_log_event"):
            log_event(logger, logging.INFO, Events.PROCESS_START, msg_type="v01")

        assert len(caplog.records) == 1
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.PROCESS_START
        assert Fields.TIMESTAMP in data
        assert Fields.REQUEST_ID in data

    def test_log_event_includes_version(self, caplog):
        logger = logging.getLogger("test_log_version")
        with caplog.at_level(logging.INFO, logger="test_log_version"):
            log_event(logger, logging.INFO, "test_event")

        data = json.loads(caplog.records[0].getMessage())
        assert Fields.VERSION in data


class TestLogHelpers:
    """Test log convenience functions."""

    def test_log_process_start_returns_timestamp(self):
        logger = logging.getLogger("test_helpers")
        start = log_process_start(logger, "pacs.008.001.01", "csv")
        assert isinstance(start, float)
        assert start > 0

    def test_log_process_success(self, caplog):
        logger = logging.getLogger("test_success")
        start = time.time()
        with caplog.at_level(logging.INFO, logger="test_success"):
            log_process_success(logger, start, "pacs.008.001.01", 10)
        assert len(caplog.records) >= 1

    def test_log_process_error(self, caplog):
        logger = logging.getLogger("test_error")
        with caplog.at_level(logging.ERROR, logger="test_error"):
            log_process_error(logger, ValueError("test"), "pacs.008.001.01")
        data = json.loads(caplog.records[0].getMessage())
        assert data["error_type"] == "ValueError"

    def test_log_validation_event_success(self, caplog):
        logger = logging.getLogger("test_val_ok")
        with caplog.at_level(logging.INFO, logger="test_val_ok"):
            log_validation_event(logger, "schema", True)
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.VALIDATION_SUCCESS

    def test_log_validation_event_failure(self, caplog):
        logger = logging.getLogger("test_val_fail")
        with caplog.at_level(logging.ERROR, logger="test_val_fail"):
            log_validation_event(
                logger, "schema", False, error=ValueError("bad")
            )
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.VALIDATION_ERROR

    def test_log_validation_event_failure_no_error(self, caplog):
        logger = logging.getLogger("test_val_fail2")
        with caplog.at_level(logging.ERROR, logger="test_val_fail2"):
            log_validation_event(logger, "data", False)
        data = json.loads(caplog.records[0].getMessage())
        assert data["error_type"] == "Unknown"

    def test_log_data_load_success(self, caplog):
        logger = logging.getLogger("test_dl_ok")
        with caplog.at_level(logging.INFO, logger="test_dl_ok"):
            log_data_load_event(logger, "csv", True, record_count=5, duration_ms=100)
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.DATA_LOAD_SUCCESS

    def test_log_data_load_failure(self, caplog):
        logger = logging.getLogger("test_dl_fail")
        with caplog.at_level(logging.ERROR, logger="test_dl_fail"):
            log_data_load_event(logger, "csv", False, error=FileNotFoundError("nope"))
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.DATA_LOAD_ERROR

    def test_log_data_load_failure_no_error(self, caplog):
        logger = logging.getLogger("test_dl_fail2")
        with caplog.at_level(logging.ERROR, logger="test_dl_fail2"):
            log_data_load_event(logger, "csv", False)
        data = json.loads(caplog.records[0].getMessage())
        assert data["error_type"] == "Unknown"

    def test_log_xml_generation_success(self, caplog):
        logger = logging.getLogger("test_xml_ok")
        with caplog.at_level(logging.INFO, logger="test_xml_ok"):
            log_xml_generation_event(
                logger, "pacs.008.001.01", True, record_count=3, duration_ms=50
            )
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.XML_GENERATE_SUCCESS

    def test_log_xml_generation_failure(self, caplog):
        logger = logging.getLogger("test_xml_fail")
        with caplog.at_level(logging.ERROR, logger="test_xml_fail"):
            log_xml_generation_event(
                logger, "pacs.008.001.01", False, error=RuntimeError("xsd fail")
            )
        data = json.loads(caplog.records[0].getMessage())
        assert data[Fields.EVENT] == Events.XML_GENERATE_ERROR

    def test_log_xml_generation_failure_no_error(self, caplog):
        logger = logging.getLogger("test_xml_fail2")
        with caplog.at_level(logging.ERROR, logger="test_xml_fail2"):
            log_xml_generation_event(logger, "pacs.008.001.01", False)
        data = json.loads(caplog.records[0].getMessage())
        assert data["error_type"] == "Unknown"


class TestExecutionSummaryTracker:
    """Test execution summary tracking."""

    def test_context_manager_success(self, caplog):
        logger = logging.getLogger("test_tracker")
        with caplog.at_level(logging.INFO, logger="test_tracker"):
            with ExecutionSummaryTracker(logger) as tracker:
                tracker.increment_processed_records(10)
                tracker.set_validation_result("schema", "PASSED")
                tracker.set_output_file(
                    os.path.join(tempfile.gettempdir(), "output.xml")
                )
                tracker.set_log_file(
                    os.path.join(tempfile.gettempdir(), "app.log")
                )

        assert tracker._get_status() == ExecutionStatus.SUCCESS
        assert tracker.total_records_processed == 10

    def test_context_manager_with_exception(self, caplog):
        logger = logging.getLogger("test_tracker_err")
        with caplog.at_level(logging.INFO, logger="test_tracker_err"):
            with pytest.raises(ValueError):
                with ExecutionSummaryTracker(logger) as tracker:
                    raise ValueError("test")

        assert tracker.has_errors
        assert tracker.aborted
        assert tracker._get_status() == ExecutionStatus.ABORTED

    def test_increment_event_count(self):
        logger = logging.getLogger("test_counts")
        tracker = ExecutionSummaryTracker(logger)
        tracker.increment_event_count("info")
        tracker.increment_event_count("warning")
        tracker.increment_event_count("error")
        assert tracker.counts["info"] == 1
        assert tracker.has_warnings
        assert tracker.has_errors

    def test_invalid_level_ignored(self):
        logger = logging.getLogger("test_invalid_lvl")
        tracker = ExecutionSummaryTracker(logger)
        tracker.increment_event_count("nonexistent")
        assert sum(tracker.counts.values()) == 0

    def test_dry_run_mode(self, caplog):
        logger = logging.getLogger("test_dry")
        with caplog.at_level(logging.INFO, logger="test_dry"):
            tracker = ExecutionSummaryTracker(logger, dry_run=True, message_type="v01")
            tracker.start()
            tracker.log_summary()

    def test_status_completed_with_warnings(self):
        logger = logging.getLogger("test_warn")
        tracker = ExecutionSummaryTracker(logger)
        tracker.increment_event_count("warning")
        assert tracker._get_status() == ExecutionStatus.COMPLETED_WITH_WARNINGS

    def test_log_summary_without_start(self, caplog):
        logger = logging.getLogger("test_no_start")
        with caplog.at_level(logging.INFO, logger="test_no_start"):
            tracker = ExecutionSummaryTracker(logger)
            tracker.log_summary()
        # duration_ms should be 0 when start_time is None


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_formats_json_message(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg='{"event": "test_event"}', args=(), exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["event"] == "test_event"

    def test_formats_plain_text(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="",
            lineno=0, msg="plain text message", args=(), exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["message"] == "plain text message"
        assert Fields.LEVEL in data

    def test_formats_with_exception(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="",
            lineno=0, msg="error occurred", args=(), exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert "exception" in data


class TestConfigureJsonLogging:
    """Test JSON logging configuration."""

    def test_default_configuration(self):
        logger = configure_json_logging(
            logging.getLogger("test_config"), console_output=False
        )
        assert logger.level == logging.INFO

    def test_with_log_file(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        logger = configure_json_logging(
            logging.getLogger("test_file"),
            log_file=log_file,
            console_output=False,
        )
        assert len(logger.handlers) == 1  # file handler only

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("PACS008_LOG_LEVEL", "DEBUG")
        logger = configure_json_logging(
            logging.getLogger("test_env"), console_output=False
        )
        assert logger.level == logging.DEBUG

    def test_env_var_log_file(self, monkeypatch, tmp_path):
        log_file = str(tmp_path / "env.log")
        monkeypatch.setenv("PACS008_LOG_FILE", log_file)
        logger = configure_json_logging(
            logging.getLogger("test_env_file"), console_output=False
        )
        assert len(logger.handlers) == 1

    def test_clears_existing_handlers(self):
        logger = logging.getLogger("test_clear")
        logger.addHandler(logging.StreamHandler())
        logger.addHandler(logging.StreamHandler())
        assert len(logger.handlers) == 2
        configure_json_logging(logger, console_output=False)
        assert len(logger.handlers) == 0


class TestExecutionMetrics:
    """Test enhanced execution metrics tracking."""

    def test_basic_lifecycle(self, caplog):
        logger = logging.getLogger("test_metrics")
        with caplog.at_level(logging.INFO, logger="test_metrics"):
            metrics = ExecutionMetrics(
                logger, "xml_generation", message_type="pacs.008.001.01"
            )
            metrics.start()
            metrics.track_phase("data_load", 120)
            metrics.track_phase("xml_gen", 350)
            metrics.track_validation("schema", "PASSED")
            metrics.increment_processed(10)
            metrics.log_telemetry()

        assert metrics.status == ExecutionStatus.SUCCESS
        assert metrics.records_processed == 10

    def test_failed_validation(self):
        logger = logging.getLogger("test_metrics_fail")
        metrics = ExecutionMetrics(logger, "validation")
        metrics.track_validation("schema", "FAILED")
        assert metrics.status == ExecutionStatus.FAILED

    def test_increment_failed(self):
        logger = logging.getLogger("test_metrics_inc_fail")
        metrics = ExecutionMetrics(logger, "processing")
        metrics.increment_failed(3)
        assert metrics.records_failed == 3
        assert metrics.status == ExecutionStatus.FAILED

    def test_set_error(self):
        logger = logging.getLogger("test_metrics_err")
        metrics = ExecutionMetrics(logger, "processing")
        metrics.set_error("something went wrong")
        assert metrics.error_message == "something went wrong"
        assert metrics.status == ExecutionStatus.FAILED

    def test_custom_request_id(self):
        logger = logging.getLogger("test_metrics_rid")
        metrics = ExecutionMetrics(
            logger, "test", request_id="req-custom01"
        )
        assert metrics.request_id == "req-custom01"

    def test_telemetry_without_start(self, caplog):
        logger = logging.getLogger("test_no_start_m")
        with caplog.at_level(logging.INFO, logger="test_no_start_m"):
            metrics = ExecutionMetrics(logger, "test")
            metrics.log_telemetry()
        # duration_ms should be 0 when start_time is None


class TestLogLevelConstants:
    """Test constant classes."""

    def test_log_levels(self):
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_execution_statuses(self):
        assert ExecutionStatus.SUCCESS == "SUCCESS"
        assert ExecutionStatus.FAILED == "FAILED"
        assert ExecutionStatus.ABORTED == "ABORTED"
        assert ExecutionStatus.COMPLETED_WITH_WARNINGS == "COMPLETED_WITH_WARNINGS"

    def test_events(self):
        assert Events.PROCESS_START == "process_start"
        assert Events.VALIDATION_ERROR == "validation_error"
        assert Events.XML_GENERATE_SUCCESS == "xml_generate_success"

    def test_fields(self):
        assert Fields.EVENT == "event"
        assert Fields.MESSAGE_TYPE == "message_type"
        assert Fields.DURATION_MS == "duration_ms"
