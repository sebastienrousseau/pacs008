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

"""Execution metrics trackers.

``ExecutionSummaryTracker`` aggregates lifecycle counters across a CLI
invocation and emits a final summary report. ``ExecutionMetrics`` adds
per-phase timing breakdowns and validation results — used by the API
layer for richer observability.
"""

import logging
import time
from typing import Any, Optional

from pacs008.observability.events import Events, log_event
from pacs008.observability.fields import ExecutionStatus
from pacs008.observability.tracing import (
    generate_request_id,
    set_request_id,
)


class ExecutionSummaryTracker:
    """Track execution metrics for a final summary report.

    Provides automatic log-event counting and lifecycle bookkeeping. Use
    as a context manager for automatic start/end tracking and summary
    emission, or call ``start`` / ``log_summary`` manually.

    Example:
        >>> import logging
        >>> with ExecutionSummaryTracker(logging.getLogger()) as tracker:
        ...     tracker.increment_processed_records(1250)
        ...     tracker.set_validation_result("schema_validation", "PASSED")
    """

    def __init__(
        self,
        logger: logging.Logger,
        dry_run: bool = False,
        message_type: Optional[str] = None,
    ):
        """Initialize the tracker.

        Args:
            logger: Logger to write the summary report to.
            dry_run: Whether this is a dry-run execution.
            message_type: ISO 20022 message type, if applicable.
        """
        self.logger = logger
        self.dry_run = dry_run
        self.message_type = message_type

        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.start_time_iso: Optional[str] = None
        self.end_time_iso: Optional[str] = None

        self.counts = {
            "debug": 0,
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
        }

        self.total_records_processed = 0
        self.validation_metrics: dict[str, str] = {}
        self.output_file: Optional[str] = None
        self.log_file: Optional[str] = None

        self.has_errors = False
        self.has_warnings = False
        self.aborted = False

    def start(self) -> None:
        """Mark execution start time."""
        self.start_time = time.time()
        self.start_time_iso = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )

    def increment_event_count(self, level: str) -> None:
        """Increment count for a specific log level.

        Args:
            level: Log level name (case-insensitive).
        """
        level_lower = level.lower()
        if level_lower in self.counts:
            self.counts[level_lower] += 1

        if level_lower in ("error", "critical"):
            self.has_errors = True
        elif level_lower == "warning":
            self.has_warnings = True

    def increment_processed_records(self, count: int = 1) -> None:
        """Increment total records processed count."""
        self.total_records_processed += count

    def set_validation_result(self, validation_type: str, result: str) -> None:
        """Record a validation result.

        Args:
            validation_type: e.g. ``schema_validation``.
            result: e.g. ``PASSED``, ``FAILED``.
        """
        self.validation_metrics[validation_type] = result

    def set_output_file(self, file_path: Optional[str]) -> None:
        """Record the output file path (or ``None`` for dry-run)."""
        self.output_file = file_path

    def set_log_file(self, file_path: str) -> None:
        """Record the log file path."""
        self.log_file = file_path

    def abort(self) -> None:
        """Mark execution as aborted."""
        self.aborted = True

    def _get_status(self) -> str:
        if self.aborted:
            return ExecutionStatus.ABORTED
        if self.has_errors:
            return ExecutionStatus.FAILED
        if self.has_warnings:
            return ExecutionStatus.COMPLETED_WITH_WARNINGS
        return ExecutionStatus.SUCCESS

    def log_summary(self) -> None:
        """Emit the execution summary report."""
        self.end_time = time.time()
        self.end_time_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        duration_ms = 0
        if self.start_time is not None:
            duration_ms = int((self.end_time - self.start_time) * 1000)

        summary_data: dict[str, Any] = {
            "status": self._get_status(),
            "execution_mode": "dry_run" if self.dry_run else "production",
            "total_records_processed": self.total_records_processed,
            "counts": self.counts,
            "performance": {
                "start_time": self.start_time_iso,
                "end_time": self.end_time_iso,
                "total_duration_ms": duration_ms,
            },
        }

        if self.validation_metrics:
            summary_data["validation_metrics"] = self.validation_metrics

        output_file_value = "None"
        if self.output_file:
            output_file_value = self.output_file
        elif self.dry_run:
            output_file_value = "None (Dry Run)"

        summary_data["artifacts"] = {
            "output_file": output_file_value,
            "log_file": self.log_file if self.log_file else "None",
        }

        if self.message_type:
            summary_data["message_type"] = self.message_type

        log_event(
            self.logger,
            logging.INFO,
            Events.EXECUTION_SUMMARY,
            message="Execution Summary Report",
            summary=summary_data,
        )

    def __enter__(self) -> "ExecutionSummaryTracker":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.increment_event_count("error")
            self.abort()
        self.log_summary()


class ExecutionMetrics:
    """Enhanced execution metrics with per-phase timing and telemetry.

    Tracks an operation across multiple phases (data load, generation,
    validation) and emits a telemetry report. Suitable for the API
    observability surface.
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        message_type: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Initialize the metrics tracker.

        Args:
            logger: Logger for telemetry output.
            operation: Operation name (e.g. ``xml_generation``).
            message_type: ISO 20022 message type, if applicable.
            request_id: Request ID for distributed tracing (auto if ``None``).
        """
        self.logger = logger
        self.operation = operation
        self.message_type = message_type
        self.request_id = request_id or generate_request_id()
        set_request_id(self.request_id)

        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.phase_timings: dict[str, int] = {}

        self.validation_results: dict[str, str] = {}

        self.records_processed = 0
        self.records_failed = 0

        self.status = ExecutionStatus.SUCCESS
        self.error_message: Optional[str] = None

    def start(self) -> None:
        """Mark operation start and emit a process-start event."""
        self.start_time = time.time()
        log_event(
            self.logger,
            logging.INFO,
            Events.PROCESS_START,
            operation=self.operation,
            message_type=self.message_type,
            request_id=self.request_id,
        )

    def track_phase(self, phase_name: str, duration_ms: int) -> None:
        """Record timing for a phase."""
        self.phase_timings[phase_name] = duration_ms

    def track_validation(self, validation_type: str, status: str) -> None:
        """Record a validation result; marks status FAILED if status is FAILED."""
        self.validation_results[validation_type] = status
        if status == "FAILED":
            self.status = ExecutionStatus.FAILED

    def increment_processed(self, count: int = 1) -> None:
        """Increment processed record count."""
        self.records_processed += count

    def increment_failed(self, count: int = 1) -> None:
        """Increment failed record count and mark status FAILED."""
        self.records_failed += count
        self.status = ExecutionStatus.FAILED

    def set_error(self, error_message: str) -> None:
        """Record an error message and mark status FAILED."""
        self.error_message = error_message
        self.status = ExecutionStatus.FAILED

    def log_telemetry(self) -> None:
        """Emit the telemetry report."""
        self.end_time = time.time()

        duration_ms = 0
        if self.start_time is not None:
            duration_ms = int((self.end_time - self.start_time) * 1000)

        telemetry_data: dict[str, Any] = {
            "operation": self.operation,
            "status": self.status,
            "duration_ms": duration_ms,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
        }

        if self.message_type:
            telemetry_data["message_type"] = self.message_type

        if self.phase_timings:
            telemetry_data["phase_timings"] = self.phase_timings

        if self.validation_results:
            telemetry_data["validation_results"] = self.validation_results

        if self.error_message:
            telemetry_data["error_message"] = self.error_message

        log_event(
            self.logger,
            (
                logging.INFO
                if self.status == ExecutionStatus.SUCCESS
                else logging.ERROR
            ),
            Events.EXECUTION_SUMMARY,
            message="Execution Telemetry",
            telemetry=telemetry_data,
        )
