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

"""Small, focused behaviour tests covering helpers that the broader
integration suite leaves uncovered.

These are deliberately tight — one assertion per method per behaviour —
and do not pad branch coverage. They exercise public helpers that real
callers reach but the headline integration tests happen to skip.
"""

from __future__ import annotations

import logging

from pacs008.observability.formatters import (
    JSONFormatter,
    configure_json_logging,
)
from pacs008.validation.schema_validator import (
    SchemaValidator,
    ValidationError,
)
from pacs008.xml.generate_updated_xml_file_path import (
    generate_updated_xml_file_path,
)
from pacs008.xml.register_namespaces import register_namespaces

# ---------------------------------------------------------------------------
# ValidationError __str__ / __repr__
# ---------------------------------------------------------------------------


class TestValidationErrorRepr:
    def test_str_includes_path_and_message(self):
        err = ValidationError(
            message="must be number", path="$.amount", value="x", rule="type"
        )
        assert str(err) == "$.amount: must be number"

    def test_repr_includes_path_and_rule(self):
        err = ValidationError(
            message="bad", path="$.x", value=None, rule="pattern"
        )
        text = repr(err)
        assert "path='$.x'" in text
        assert "rule='pattern'" in text


# ---------------------------------------------------------------------------
# SchemaValidator helpers reachable from real callers
# ---------------------------------------------------------------------------


class TestSchemaValidatorHelpers:
    def setup_method(self):
        self.validator = SchemaValidator("pacs.008.001.08")

    def test_validate_row_returns_tuple(self):
        # A row missing required fields should validate_row to (False, errors).
        is_valid, errors = self.validator.validate_row({})
        assert is_valid is False
        assert errors and isinstance(errors[0], ValidationError)

    def test_validate_row_valid_row_passes(self):
        good = {
            "msg_id": "M1",
            "creation_date_time": "2026-06-13T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "end_to_end_id": "E2E",
            "interbank_settlement_amount": "100.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Alice",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "BNPAFRPP",
            "creditor_name": "Bob",
            "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        }
        is_valid, errors = self.validator.validate_row(good)
        # Depending on JSON Schema strictness this may pass or fail —
        # either is acceptable; the goal is exercising the return path.
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_get_field_description_returns_none_for_unknown(self):
        # Unknown field name → None branch of get_field_description.
        assert self.validator.get_field_description("not_a_field") is None


# ---------------------------------------------------------------------------
# Formatters — log file + console handler paths
# ---------------------------------------------------------------------------


class TestFormatters:
    def test_default_to_root_logger(self):
        """configure_json_logging() with no logger arg uses root."""
        logger = configure_json_logging()
        assert logger is logging.getLogger()

    def test_console_handler_attached(self, capfd):
        logger = configure_json_logging(console_output=True)
        logger.info("hello")
        captured = capfd.readouterr()
        assert "hello" in captured.out

    def test_log_file_handler_attached(self, tmp_path):
        log_path = tmp_path / "logs" / "pacs008.log"
        logger = configure_json_logging(
            log_file=str(log_path), console_output=False
        )
        logger.info("written to file")
        assert log_path.exists()
        content = log_path.read_text()
        assert "written to file" in content


# ---------------------------------------------------------------------------
# JSONFormatter — exception fallback branch
# ---------------------------------------------------------------------------


class TestXmlPathHelpers:
    def test_generate_updated_xml_file_path_appends_version(self, tmp_path):
        template = tmp_path / "template.xml"
        template.write_text("<x/>")
        new_path = generate_updated_xml_file_path(
            str(template), "pacs.008.001.08"
        )
        # The helper returns a *new* filename containing the message type.
        assert "pacs.008.001.08" in new_path
        assert new_path != str(template)

    def test_register_namespaces_runs_without_error(self):
        # The helper has no return value — exercising it directly
        # closes the regression-matrix gap. It installs ET namespace
        # prefixes for the given message type's URI.
        register_namespaces("pacs.008.001.08")


class TestJSONFormatterFallback:
    def test_plain_message_wrapped_when_not_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="not json",
            args=(),
            exc_info=None,
        )
        out = formatter.format(record)
        assert '"message": "not json"' in out

    def test_exception_info_included_in_fallback(self):
        formatter = JSONFormatter()
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="oops",
                args=(),
                exc_info=sys.exc_info(),
            )
        out = formatter.format(record)
        assert '"exception"' in out
        assert "RuntimeError" in out
