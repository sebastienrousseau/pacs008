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

"""Request-id tracing for distributed observability.

A ``ContextVar`` carries a short request identifier across async tasks so
every log line emitted during a single ``process_files`` / API request
shares the same ``request_id`` field — the prerequisite for correlating
logs across services in DORA-aligned audit trails.
"""

import uuid
from contextvars import ContextVar
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pacs008")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


_request_id_context: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)


def generate_request_id() -> str:
    """Generate a unique request ID for request tracing.

    Returns:
        A short UUID-based request ID in the form ``req-<8 hex chars>``.

    Example:
        >>> rid = generate_request_id()
        >>> rid.startswith("req-") and len(rid) == 12
        True
    """
    return f"req-{uuid.uuid4().hex[:8]}"


def get_request_id() -> str:
    """Get or create request ID for the current context.

    If no request ID has been set in this context, one is generated and
    stored so subsequent calls within the same context return the same
    value.

    Returns:
        The request ID for the current execution context.
    """
    request_id = _request_id_context.get()
    if request_id is None:
        request_id = generate_request_id()
        _request_id_context.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """Set request ID for the current context.

    Useful for API handlers that want to propagate an upstream
    request/trace ID (e.g. from an ``X-Request-Id`` header) into log
    output.

    Args:
        request_id: The request ID to set.
    """
    _request_id_context.set(request_id)
