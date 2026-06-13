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

"""Event-name constants and structured event-logging helpers.

The ``Events`` class is a namespace of event-name constants used as the
canonical event identifier across the codebase. ``log_event`` and the
``log_*_event`` family wrap ``logger.log`` with timestamp, level,
request id, version, and PII-redacted fields, emitting a single flat
JSON object per call.
"""

import json
import logging
import time
from typing import Any

from pacs008.observability.fields import Fields
from pacs008.observability.redaction import _redact_pii_from_dict
from pacs008.observability.tracing import __version__, get_request_id


class Events:
    """Standardized event names for structured logging."""

    # Process lifecycle events
    PROCESS_START = "process_start"
    PROCESS_SUCCESS = "process_success"
    PROCESS_ERROR = "process_error"
    EXECUTION_SUMMARY = "execution_summary"

    # CLI events
    CLI_ARGS_PARSED = "cli_args_parsed"
    CLI_DRY_RUN = "cli_dry_run"

    # Validation events
    VALIDATION_START = "validation_start"
    VALIDATION_SUCCESS = "validation_success"
    VALIDATION_ERROR = "validation_error"

    # Data loading events
    DATA_LOAD_START = "data_load_start"
    DATA_LOAD_SUCCESS = "data_load_success"
    DATA_LOAD_ERROR = "data_load_error"

    # XML generation events
    XML_GENERATE_START = "xml_generate_start"
    XML_GENERATE_SUCCESS = "xml_generate_success"
    XML_GENERATE_ERROR = "xml_generate_error"

    # XSD validation events
    XSD_VALIDATION_START = "xsd_validation_start"
    XSD_VALIDATION_SUCCESS = "xsd_validation_success"
    XSD_VALIDATION_ERROR = "xsd_validation_error"

    # Namespace registration events
    NAMESPACE_REGISTER = "namespace_register"


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Log a structured event with standardised format and PII redaction.

    Automatically adds:

    - ``request_id`` for distributed tracing
    - ISO 8601 UTC timestamp
    - Library version
    - Logger name and level

    All values are passed through PII redaction (``_redact_pii_from_dict``)
    before being JSON-encoded.

    Args:
        logger: The logger instance to use.
        level: Logging level (``logging.INFO``, ``logging.ERROR``, …).
        event: Event name (use ``Events`` constants).
        **fields: Additional fields to include in the log entry.
    """

    log_data = {
        Fields.TIMESTAMP: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        Fields.LEVEL: logging.getLevelName(level),
        Fields.LOGGER_NAME: logger.name,
        Fields.REQUEST_ID: get_request_id(),
        Fields.EVENT: event,
        Fields.VERSION: __version__,
        **fields,
    }

    redacted_data = _redact_pii_from_dict(log_data)
    logger.log(level, json.dumps(redacted_data, sort_keys=True))


def log_process_start(
    logger: logging.Logger,
    message_type: str,
    data_source_type: str,
    **extra_fields: Any,
) -> float:
    """Log a process-start event and return the start timestamp.

    Args:
        logger: The logger instance.
        message_type: ISO 20022 message type.
        data_source_type: ``csv``, ``sqlite``, ``list``, ``dict``, …
        **extra_fields: Additional fields to include.

    Returns:
        Start timestamp (seconds since epoch) for duration calculation.
    """
    start_time = time.time()
    log_event(
        logger,
        logging.INFO,
        Events.PROCESS_START,
        message_type=message_type,
        data_source_type=data_source_type,
        **extra_fields,
    )
    return start_time


def log_process_success(
    logger: logging.Logger,
    start_time: float,
    message_type: str,
    record_count: int,
    **extra_fields: Any,
) -> None:
    """Log a process-success event with elapsed duration.

    Args:
        logger: The logger instance.
        start_time: Timestamp returned by ``log_process_start``.
        message_type: ISO 20022 message type.
        record_count: Number of records processed.
        **extra_fields: Additional fields to include.
    """
    duration_ms = int((time.time() - start_time) * 1000)
    log_event(
        logger,
        logging.INFO,
        Events.PROCESS_SUCCESS,
        message_type=message_type,
        record_count=record_count,
        duration_ms=duration_ms,
        **extra_fields,
    )


def log_process_error(
    logger: logging.Logger,
    error: Exception,
    message_type: str | None = None,
    **extra_fields: Any,
) -> None:
    """Log a process-error event.

    Args:
        logger: The logger instance.
        error: The exception that occurred.
        message_type: ISO 20022 message type, if known.
        **extra_fields: Additional fields to include.
    """
    log_event(
        logger,
        logging.ERROR,
        Events.PROCESS_ERROR,
        error_type=type(error).__name__,
        error_message=str(error),
        message_type=message_type,
        **extra_fields,
    )


def log_validation_event(
    logger: logging.Logger,
    validation_type: str,
    success: bool,
    error: Exception | None = None,
    **extra_fields: Any,
) -> None:
    """Log a validation event (success or error).

    Args:
        logger: The logger instance.
        validation_type: ``schema``, ``data``, ``business_rules``, …
        success: Whether validation succeeded.
        error: Exception if validation failed.
        **extra_fields: Additional fields to include.
    """
    if success:
        log_event(
            logger,
            logging.INFO,
            Events.VALIDATION_SUCCESS,
            validation_type=validation_type,
            **extra_fields,
        )
    else:
        log_event(
            logger,
            logging.ERROR,
            Events.VALIDATION_ERROR,
            validation_type=validation_type,
            error_type=type(error).__name__ if error else "Unknown",
            error_message=str(error) if error else "Validation failed",
            **extra_fields,
        )


def log_data_load_event(
    logger: logging.Logger,
    data_source_type: str,
    success: bool,
    record_count: int | None = None,
    error: Exception | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log a data-loading event.

    Args:
        logger: The logger instance.
        data_source_type: ``csv``, ``sqlite``, ``list``, ``dict``, …
        success: Whether data loading succeeded.
        record_count: Number of records loaded (if success).
        error: Exception if loading failed.
        duration_ms: Loading duration in milliseconds.
    """
    if success:
        log_event(
            logger,
            logging.INFO,
            Events.DATA_LOAD_SUCCESS,
            data_source_type=data_source_type,
            record_count=record_count,
            duration_ms=duration_ms,
        )
    else:
        log_event(
            logger,
            logging.ERROR,
            Events.DATA_LOAD_ERROR,
            data_source_type=data_source_type,
            error_type=type(error).__name__ if error else "Unknown",
            error_message=str(error) if error else "Data load failed",
        )


def log_xml_generation_event(
    logger: logging.Logger,
    message_type: str,
    success: bool,
    record_count: int | None = None,
    error: Exception | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log an XML-generation event.

    Args:
        logger: The logger instance.
        message_type: ISO 20022 message type.
        success: Whether XML generation succeeded.
        record_count: Number of records in generated XML.
        error: Exception if generation failed.
        duration_ms: Generation duration in milliseconds.
    """
    if success:
        log_event(
            logger,
            logging.INFO,
            Events.XML_GENERATE_SUCCESS,
            message_type=message_type,
            record_count=record_count,
            duration_ms=duration_ms,
        )
    else:
        log_event(
            logger,
            logging.ERROR,
            Events.XML_GENERATE_ERROR,
            message_type=message_type,
            error_type=type(error).__name__ if error else "Unknown",
            error_message=str(error) if error else "XML generation failed",
        )
