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

"""Tests for the optional OpenTelemetry tracing helpers."""

from __future__ import annotations

import pytest

# These imports require the [otel] extra to be installed.
otel_api = pytest.importorskip("opentelemetry")
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from pacs008.observability.otel import (
    add_attribute,
    is_enabled,
    trace_span,
)


@pytest.fixture
def exporter():
    """Wire an in-memory span exporter as the global TracerProvider."""
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    # Reset the global provider so the test sees its own spans.
    otel_trace._TRACER_PROVIDER = provider  # type: ignore[attr-defined]
    yield exp
    exp.clear()


# ---------------------------------------------------------------------------
# is_enabled — env-var gating
# ---------------------------------------------------------------------------


class TestIsEnabled:
    def test_enabled_by_default(self, monkeypatch):
        monkeypatch.delenv("PACS008_OTEL_ENABLED", raising=False)
        assert is_enabled() is True

    @pytest.mark.parametrize("v", ["0", "false", "FALSE", "no", "off"])
    def test_disabled_via_env(self, monkeypatch, v):
        monkeypatch.setenv("PACS008_OTEL_ENABLED", v)
        assert is_enabled() is False

    def test_enabled_via_env_truthy(self, monkeypatch):
        monkeypatch.setenv("PACS008_OTEL_ENABLED", "1")
        assert is_enabled() is True


# ---------------------------------------------------------------------------
# trace_span — span emission
# ---------------------------------------------------------------------------


class TestTraceSpan:
    def test_span_emitted(self, exporter):
        with trace_span("validate"):
            pass
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "validate"

    def test_attributes_recorded(self, exporter):
        with trace_span(
            "validate",
            attributes={
                "pacs008.scheme": "cbpr_plus",
                "payment.uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            },
        ):
            pass
        spans = exporter.get_finished_spans()
        attrs = dict(spans[0].attributes)
        assert attrs["pacs008.scheme"] == "cbpr_plus"
        assert (
            attrs["payment.uetr"]
            == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        )

    def test_none_attributes_skipped(self, exporter):
        with trace_span(
            "validate",
            attributes={"keep": "yes", "skip": None},
        ):
            pass
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert "keep" in attrs
        assert "skip" not in attrs

    def test_exception_marks_span_error(self, exporter):
        with pytest.raises(RuntimeError):
            with trace_span("boom"):
                raise RuntimeError("nope")
        spans = exporter.get_finished_spans()
        assert spans[0].status.status_code == otel_trace.StatusCode.ERROR

    def test_disabled_is_noop(self, monkeypatch, exporter):
        monkeypatch.setenv("PACS008_OTEL_ENABLED", "false")
        with trace_span("validate") as span:
            assert span is None
        assert exporter.get_finished_spans() == ()


# ---------------------------------------------------------------------------
# add_attribute — nested attribute setting
# ---------------------------------------------------------------------------


class TestAddAttribute:
    def test_attribute_added_inside_span(self, exporter):
        with trace_span("validate"):
            add_attribute("payment.uetr", "abc-123")
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert attrs["payment.uetr"] == "abc-123"

    def test_no_active_span_is_noop(self, exporter):
        add_attribute("orphan", "value")  # should not raise
        assert exporter.get_finished_spans() == ()

    def test_none_value_skipped(self, exporter):
        with trace_span("validate"):
            add_attribute("nope", None)
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        assert "nope" not in attrs

    def test_complex_value_stringified(self, exporter):
        with trace_span("validate"):
            add_attribute("collection", {"a": 1})
        attrs = dict(exporter.get_finished_spans()[0].attributes)
        # dict gets str()'d.
        assert isinstance(attrs["collection"], str)
        assert "a" in attrs["collection"]
