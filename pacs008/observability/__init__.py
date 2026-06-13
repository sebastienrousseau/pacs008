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

"""Structured observability for pacs008.

This package houses everything related to logging, tracing, metrics, and
PII redaction. It replaces the monolithic ``pacs008.logging_schema``
module while preserving the public API.

Sub-modules:

- :mod:`pacs008.observability.fields` — log field/level constants.
- :mod:`pacs008.observability.events` — event-name constants and the
  ``log_event`` helpers.
- :mod:`pacs008.observability.tracing` — request-id ``ContextVar`` for
  distributed tracing.
- :mod:`pacs008.observability.redaction` — PII masking and log-injection
  sanitisation.
- :mod:`pacs008.observability.formatters` — JSON formatter and
  ``configure_json_logging`` setup helper.
- :mod:`pacs008.observability.metrics` — execution summary and telemetry
  trackers.

Existing code can import either from this package or from
``pacs008.logging_schema`` (kept as a re-export shim for backward
compatibility).
"""

from pacs008.observability.events import (
    Events,
    log_data_load_event,
    log_event,
    log_process_error,
    log_process_start,
    log_process_success,
    log_validation_event,
    log_xml_generation_event,
)
from pacs008.observability.fields import ExecutionStatus, Fields, LogLevel
from pacs008.observability.formatters import (
    JSONFormatter,
    configure_json_logging,
)
from pacs008.observability.metrics import (
    ExecutionMetrics,
    ExecutionSummaryTracker,
)
from pacs008.observability.redaction import mask_sensitive_data
from pacs008.observability.tracing import (
    generate_request_id,
    get_request_id,
    set_request_id,
)

__all__ = [
    "Events",
    "ExecutionMetrics",
    "ExecutionStatus",
    "ExecutionSummaryTracker",
    "Fields",
    "JSONFormatter",
    "LogLevel",
    "configure_json_logging",
    "generate_request_id",
    "get_request_id",
    "log_data_load_event",
    "log_event",
    "log_process_error",
    "log_process_start",
    "log_process_success",
    "log_validation_event",
    "log_xml_generation_event",
    "mask_sensitive_data",
    "set_request_id",
]
