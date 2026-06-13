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

"""Optional OpenTelemetry tracing for pacs008.

OpenTelemetry is the de facto standard for distributed tracing — a
near-requirement for DORA-aligned audit trails in the EU and for
modern observability stacks generally. This module wires lightweight
spans around the pacs008 pipeline **without** taking a hard
dependency on the OTel SDK.

Behaviour:

- If ``opentelemetry`` is not importable, every API in this module
  becomes a no-op. Callers get the convenience of always-callable
  helpers without conditional imports at every call site.
- The ``PACS008_OTEL_ENABLED`` environment variable also gates the
  helpers; setting it to ``"0"`` or ``"false"`` turns them off even
  when ``opentelemetry`` is installed.
- Spans carry ``pacs008.message_type``, ``pacs008.scheme``,
  ``payment.uetr`` and similar attributes so traces survive PII
  redaction in downstream collectors.

Install OpenTelemetry to enable::

    pip install pacs008[otel]
    # or
    pip install opentelemetry-api opentelemetry-sdk
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from typing import Any

try:
    from opentelemetry import trace as _otel_trace

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _otel_trace = None  # type: ignore[assignment]
    _OTEL_AVAILABLE = False


_TRACER_NAME = "pacs008"


def is_enabled() -> bool:
    """Return ``True`` iff OTel tracing should fire.

    Honours both the import availability of ``opentelemetry`` and the
    ``PACS008_OTEL_ENABLED`` env var (``"0"`` / ``"false"`` / ``"no"``
    disable; everything else, including unset, defaults to enabled
    when the SDK is present).
    """
    if not _OTEL_AVAILABLE:
        return False
    raw = os.environ.get("PACS008_OTEL_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


@contextlib.contextmanager
def trace_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Open a tracing span, no-op when OTel is unavailable.

    Yields the span object when active, ``None`` otherwise. Use::

        with trace_span("validate", attributes={"scheme": "cbpr_plus"}):
            ...

    The yielded span has ``set_attribute`` / ``record_exception``
    methods you can call inside the ``with`` block.
    """
    if not is_enabled():
        yield None
        return

    tracer = _otel_trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, _attr_value(value))
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(_otel_trace.StatusCode.ERROR)
            raise


def add_attribute(key: str, value: Any) -> None:
    """Add an attribute to the currently active span.

    No-op when OTel is unavailable or when there is no active span.
    """
    if not is_enabled() or value is None:
        return
    span = _otel_trace.get_current_span()
    if span is None or not span.is_recording():
        return
    span.set_attribute(key, _attr_value(value))


def _attr_value(value: Any) -> Any:
    """Coerce attribute values to types OTel accepts."""
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_attr_value(v) for v in value]
    return str(value)
