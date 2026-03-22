"""Final coverage tests: close all 6 remaining branch gaps to reach 100%.

Targets:
  1. job_manager.py:175->exit    cleanup when completed_jobs <= keep_count
  2. swift_charset.py:310->329   cleanse_data_with_report(cleanse_charset=False)
  3. swift_charset.py:329->335   cleanse_data_with_report(enforce_lengths=False)
  4. context.py:103->exit         set_log_level when self.logger is None
  5. core.py:45->54               logger already has handlers on reload
  6. parquet:155->152              empty batch from parquet iteration
"""

import importlib
import logging
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pacs008.api.job_manager import JobManager, JobStatus
from pacs008.compliance.swift_charset import (
    cleanse_data_with_report,
    validate_swift_charset,
)
from pacs008.context.context import Context

# --- 1. job_manager.py:175->exit ---


class TestCleanupNoExcess:
    """cleanup_old_jobs when completed jobs <= keep_count (no pruning)."""

    def test_cleanup_no_pruning_needed(self):
        mgr = JobManager()
        # Create 2 completed jobs, keep_count=5 → no pruning
        for _ in range(2):
            jid = mgr.create_job()
            mgr.update_status(jid, JobStatus.SUCCESS)
        mgr.cleanup_old_jobs(keep_count=5)
        assert len(mgr.jobs) == 2  # All retained

    def test_cleanup_exact_count(self):
        mgr = JobManager()
        # Create exactly keep_count completed jobs → no pruning
        for _ in range(3):
            jid = mgr.create_job()
            mgr.update_status(jid, JobStatus.FAILED)
        mgr.cleanup_old_jobs(keep_count=3)
        assert len(mgr.jobs) == 3

    def test_cleanup_zero_completed(self):
        mgr = JobManager()
        mgr.create_job()  # Pending, not completed
        mgr.cleanup_old_jobs(keep_count=1)
        assert len(mgr.jobs) == 1


# --- 2 & 3. swift_charset.py:310->329, 329->335 ---


class TestCleanseDataWithReportFlags:
    """Test cleanse_data_with_report with individual flags disabled."""

    def _dirty_row(self):
        return {
            "msg_id": "X" * 50,  # Too long (max 35)
            "debtor_name": "Müller™",  # Non-SWIFT chars
            "creditor_name": "García",  # Non-SWIFT chars
        }

    def test_charset_disabled_lengths_enabled(self):
        """cleanse_charset=False skips charset pass (310->329)."""
        data = [self._dirty_row()]
        result, report = cleanse_data_with_report(
            data, cleanse_charset=False, enforce_lengths=True
        )
        # Unicode chars should be preserved (charset not cleansed)
        assert "ü" in result[0]["debtor_name"]
        # But msg_id should be truncated (lengths enforced)
        assert len(result[0]["msg_id"]) == 35
        assert report.rows_modified >= 1

    def test_lengths_disabled_charset_enabled(self):
        """enforce_lengths=False skips length pass (329->335)."""
        data = [self._dirty_row()]
        result, report = cleanse_data_with_report(
            data, cleanse_charset=True, enforce_lengths=False
        )
        # Unicode should be transliterated
        assert "ü" not in result[0]["debtor_name"]
        assert validate_swift_charset(result[0]["debtor_name"]) == []
        # But msg_id should NOT be truncated
        assert len(result[0]["msg_id"]) == 50
        assert report.rows_modified >= 1

    def test_both_disabled(self):
        """Both flags disabled → no modifications."""
        data = [self._dirty_row()]
        result, report = cleanse_data_with_report(
            data, cleanse_charset=False, enforce_lengths=False
        )
        assert result[0]["debtor_name"] == "Müller™"
        assert len(result[0]["msg_id"]) == 50
        assert report.rows_modified == 0
        assert report.is_clean


# --- 4. context.py:103->exit ---


class TestContextLoggerNone:
    """set_log_level when self.logger is None/falsy (103->exit)."""

    @pytest.fixture(autouse=True)
    def reset_context(self):
        Context.instance = None
        yield
        Context.instance = None

    def test_set_log_level_with_logger_none(self):
        """set_log_level skips setLevel when self.logger is None."""
        ctx = Context.get_instance()
        # __init__ sets self.logger to a Logger, so manually set to None
        # to test the defensive branch at line 103
        ctx.logger = None
        ctx.set_log_level("WARNING")
        assert ctx.log_level == logging.WARNING
        assert ctx.logger is None  # Still None, setLevel was skipped

    def test_set_log_level_with_logger_present(self):
        """set_log_level calls setLevel when logger exists."""
        ctx = Context.get_instance()
        # logger is set by __init__ to a real Logger
        assert ctx.logger is not None
        ctx.set_log_level("ERROR")
        assert ctx.log_level == logging.ERROR
        assert ctx.logger.level == logging.ERROR


# --- 5. core.py:45->54 ---


class TestCoreLoggerHandlers:
    """Cover the 'logger already has handlers' branch at module level."""

    def test_logger_handlers_branch(self):
        """Force re-evaluation of the handler guard."""
        import pacs008.core.core as core_mod

        logger = logging.getLogger(core_mod.__name__)
        # Logger should already have a handler from initial import
        assert len(logger.handlers) >= 1
        # Reload the module — the 'if not logger.handlers' is now False
        # so it skips adding another handler (covers 45->54)
        handler_count_before = len(logger.handlers)
        importlib.reload(core_mod)
        # Should NOT have added another handler
        assert len(logger.handlers) == handler_count_before


# --- 6. parquet:155->152 ---


class TestParquetEmptyBatch:
    """Cover the empty chunk_data branch in streaming parquet loader."""

    def test_empty_batch_skipped(self, tmp_path):
        """When iter_batches yields an empty batch, it should be skipped."""
        from pacs008.parquet.load_parquet_data import (
            load_parquet_data_streaming,
        )

        # Create a small parquet file
        table = pa.table({"col": [1, 2, 3]})
        path = tmp_path / "test.parquet"
        pq.write_table(table, str(path))

        # Mock iter_batches to yield an empty batch followed by real data
        empty_batch = MagicMock()
        empty_batch.to_pylist.return_value = []  # Empty chunk

        real_batch = MagicMock()
        real_batch.to_pylist.return_value = [{"col": 1}]

        with patch(
            "pacs008.parquet.load_parquet_data.pq.ParquetFile"
        ) as mock_pf:
            mock_pf.return_value.iter_batches.return_value = [
                empty_batch,
                real_batch,
            ]
            chunks = list(load_parquet_data_streaming(str(path), chunk_size=1))

        # Only the non-empty batch should be yielded
        assert len(chunks) == 1
        assert chunks[0] == [{"col": 1}]
