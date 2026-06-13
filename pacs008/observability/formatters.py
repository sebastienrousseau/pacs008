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

"""JSON log formatter and global logging configuration helper."""

import json
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union

from pacs008.observability.fields import Fields
from pacs008.observability.tracing import __version__, get_request_id


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging output.

    Ensures every log record is emitted as valid JSON regardless of the
    calling site. ``log_event`` already emits JSON; this formatter wraps
    plain ``logger.info("…")`` style calls into the same envelope so
    aggregation pipelines see one shape.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: ``LogRecord`` to format.

        Returns:
            JSON-encoded log entry.
        """

        try:
            # If the message is already JSON (from log_event), pass through.
            log_data: dict[str, Any] = json.loads(record.getMessage())
        except (json.JSONDecodeError, ValueError):
            log_data = {
                Fields.TIMESTAMP: time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
                ),
                Fields.LEVEL: record.levelname,
                Fields.LOGGER_NAME: record.name,
                Fields.REQUEST_ID: get_request_id(),
                Fields.VERSION: __version__,
                "message": record.getMessage(),
            }

            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, sort_keys=True)


def configure_json_logging(
    logger: Optional[logging.Logger] = None,
    level: Union[str, int] = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_output: bool = True,
) -> logging.Logger:
    """Configure structured JSON logging.

    Environment variable overrides:

    - ``PACS008_LOG_LEVEL`` — sets the level (DEBUG/INFO/…)
    - ``PACS008_LOG_FILE`` — sets a file destination

    Args:
        logger: Logger to configure (defaults to root logger).
        level: Minimum log level.
        log_file: Path to log file (``None`` = console only).
        max_bytes: Max file size before rotation (default 10MB).
        backup_count: Number of rotated backups to keep.
        console_output: Whether to log to stdout.

    Returns:
        The configured logger.
    """
    if logger is None:
        logger = logging.getLogger()

    env_level = os.environ.get("PACS008_LOG_LEVEL")
    if env_level:
        level = getattr(logging, env_level.upper(), level)

    env_log_file = os.environ.get("PACS008_LOG_FILE")
    if env_log_file:
        log_file = env_log_file

    logger.handlers = []
    logger.setLevel(level)

    formatter = JSONFormatter()

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
