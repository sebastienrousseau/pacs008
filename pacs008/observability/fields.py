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

"""Log field and level constants.

These classes contain the field-name and log-level string constants used
by ``log_event`` and the JSON formatter. They are intentionally minimal
namespaces — no instances are created.
"""


class LogLevel:
    """Standard log level names for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExecutionStatus:
    """High-level execution status for summary reports."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    ABORTED = "ABORTED"


class Fields:
    """Standardized field names for structured logging."""

    # Core fields (always present)
    EVENT = "event"
    TIMESTAMP = "timestamp"
    LEVEL = "level"
    REQUEST_ID = "request_id"  # UUID for request tracing
    LOGGER_NAME = "logger"

    # Component identification
    COMPONENT = "component"
    MODULE = "module"
    FUNCTION = "function"
    VERSION = "version"  # Pacs008 library version

    # Message type and version
    MESSAGE_TYPE = "message_type"
    ISO_VERSION = "iso_version"
    DRY_RUN = "dry_run"
    BANK_PROFILE = "bank_profile"  # e.g., hsbc_uk, jpm_cbpr_plus

    # File paths (never log sensitive data)
    TEMPLATE_PATH = "template_path"
    SCHEMA_PATH = "schema_path"
    DATA_SOURCE_TYPE = "data_source_type"  # csv, sqlite, list, dict

    # Record counts and statistics
    RECORD_COUNT = "record_count"
    TRANSACTION_COUNT = "transaction_count"

    # Performance metrics
    DURATION_MS = "duration_ms"
    SIZE_BYTES = "size_bytes"

    # Error information (flat structure)
    ERROR_TYPE = "error_type"
    ERROR_MESSAGE = "error_message"
    ERROR_FIELD = "error_field"
    ERROR_INVALID_VALUE = "error_invalid_value"  # masked if PII
    ERROR_REASON = "error_reason"

    # Validation details
    VALIDATION_TYPE = "validation_type"  # schema, data, business_rules
    END_TO_END_ID = "end_to_end_id"  # Transaction reference for tracing
