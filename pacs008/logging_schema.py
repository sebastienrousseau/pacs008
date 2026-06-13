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

"""Backward-compatibility shim for ``pacs008.observability``.

The original 1,000+ line module has been split into the
:mod:`pacs008.observability` package. This module re-exports the
public (and tested-private) API so existing imports keep working:

    from pacs008.logging_schema import Events, log_event  # still works

New code should import directly from :mod:`pacs008.observability` or one
of its sub-modules.
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
from pacs008.observability.redaction import (
    _redact_pii_from_dict,  # noqa: F401  re-exported for backward-compat tests
    _sanitize_value,  # noqa: F401  re-exported for backward-compat tests
    mask_sensitive_data,
)
from pacs008.observability.tracing import (
    __version__,
    _request_id_context,  # noqa: F401  re-exported for backward-compat tests
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
    "__version__",
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
