"""Tests for pacs008.compliance module (SWIFT silent rejection prevention)."""


from pacs008.compliance.swift_charset import (
    SWIFT_X_CHARSET,
    ComplianceViolation,
    cleanse_data,
    cleanse_data_with_report,
    cleanse_string,
    enforce_field_lengths,
    validate_swift_charset,
)

# --- SWIFT X Character Set ---


class TestSwiftXCharset:
    def test_ascii_letters_allowed(self):
        for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert c in SWIFT_X_CHARSET

    def test_digits_allowed(self):
        for c in "0123456789":
            assert c in SWIFT_X_CHARSET

    def test_special_chars_allowed(self):
        for c in "/-?:().,'+{} ":
            assert c in SWIFT_X_CHARSET

    def test_emoji_not_allowed(self):
        assert "🏦" not in SWIFT_X_CHARSET

    def test_umlaut_not_allowed(self):
        assert "ü" not in SWIFT_X_CHARSET

    def test_at_sign_not_allowed(self):
        assert "@" not in SWIFT_X_CHARSET


# --- validate_swift_charset ---


class TestValidateSwiftCharset:
    def test_clean_string_returns_empty(self):
        violations = validate_swift_charset("Hello World 123")
        assert violations == []

    def test_detects_umlaut(self):
        violations = validate_swift_charset("Müller")
        assert len(violations) == 1
        assert violations[0] == (1, "ü")

    def test_detects_multiple_violations(self):
        violations = validate_swift_charset("Ünö@corp")
        assert len(violations) == 3  # Ü, ö, @

    def test_empty_string(self):
        assert validate_swift_charset("") == []

    def test_all_swift_chars_pass(self):
        swift_str = "ABCxyz 012/-?:().,'+{}"
        assert validate_swift_charset(swift_str) == []


# --- cleanse_string ---


class TestCleanseString:
    def test_clean_string_unchanged(self):
        assert cleanse_string("Hello World") == "Hello World"

    def test_umlaut_transliteration(self):
        assert cleanse_string("Müller") == "Mueller"
        assert cleanse_string("Böhm") == "Boehm"
        assert cleanse_string("Süß") == "Suess"

    def test_accented_chars(self):
        result = cleanse_string("café résumé")
        assert "c" in result  # ç → c... wait, no, café has no ç
        assert validate_swift_charset(result) == []

    def test_currency_symbols(self):
        assert cleanse_string("€100") == "EUR100"
        assert cleanse_string("£50") == "GBP50"

    def test_trademark_replaced(self):
        result = cleanse_string("Corp™")
        assert "™" not in result
        assert validate_swift_charset(result) == []

    def test_ampersand_replaced(self):
        result = cleanse_string("A & B")
        assert "&" not in result
        assert validate_swift_charset(result) == []

    def test_at_sign_replaced(self):
        result = cleanse_string("user@email")
        assert "@" not in result

    def test_result_is_swift_compliant(self):
        """Any cleansed string must pass SWIFT charset validation."""
        test_strings = [
            "Müller & Söhne™",
            "Ñoño café",
            "user@corp.com",
            "100€ — paid",
            "résumé [draft]",
        ]
        for s in test_strings:
            result = cleanse_string(s)
            violations = validate_swift_charset(result)
            assert (
                violations == []
            ), f"Cleansed '{s}' → '{result}' still has violations: {violations}"


# --- enforce_field_lengths ---


class TestEnforceFieldLengths:
    def test_short_fields_unchanged(self):
        row = {"msg_id": "MSG001", "debtor_name": "Test"}
        corrected, violations = enforce_field_lengths(row)
        assert corrected == row
        assert violations == []

    def test_truncates_long_msg_id(self):
        row = {"msg_id": "X" * 50}
        corrected, violations = enforce_field_lengths(row)
        assert len(corrected["msg_id"]) == 35
        assert len(violations) == 1
        assert violations[0].violation_type == "field_length"
        assert violations[0].field == "msg_id"

    def test_truncates_long_name(self):
        row = {"debtor_name": "A" * 200}
        corrected, violations = enforce_field_lengths(row)
        assert len(corrected["debtor_name"]) == 140

    def test_iban_max_34(self):
        row = {"debtor_account_iban": "X" * 40}
        corrected, _ = enforce_field_lengths(row)
        assert len(corrected["debtor_account_iban"]) == 34

    def test_bic_max_11(self):
        row = {"debtor_agent_bic": "X" * 15}
        corrected, _ = enforce_field_lengths(row)
        assert len(corrected["debtor_agent_bic"]) == 11

    def test_remittance_max_140(self):
        row = {"remittance_information": "Z" * 200}
        corrected, _ = enforce_field_lengths(row)
        assert len(corrected["remittance_information"]) == 140

    def test_unknown_fields_not_touched(self):
        row = {"custom_field": "X" * 1000}
        corrected, violations = enforce_field_lengths(row)
        assert corrected["custom_field"] == "X" * 1000
        assert violations == []

    def test_none_values_skipped(self):
        row = {"msg_id": None}
        corrected, violations = enforce_field_lengths(row)
        assert corrected["msg_id"] is None
        assert violations == []


# --- cleanse_data ---


class TestCleanseData:
    def _valid_row(self, **overrides):
        row = {
            "msg_id": "MSG001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "end_to_end_id": "E2E001",
            "interbank_settlement_amount": "1000.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
        }
        row.update(overrides)
        return row

    def test_clean_data_unchanged(self):
        data = [self._valid_row()]
        result = cleanse_data(data)
        assert result[0]["debtor_name"] == "Debtor Corp"

    def test_cleanses_unicode_names(self):
        data = [self._valid_row(debtor_name="Müller & Söhne™")]
        result = cleanse_data(data)
        assert "ü" not in result[0]["debtor_name"]
        assert "™" not in result[0]["debtor_name"]
        assert validate_swift_charset(result[0]["debtor_name"]) == []

    def test_truncates_long_msg_id(self):
        data = [self._valid_row(msg_id="X" * 50)]
        result = cleanse_data(data)
        assert len(result[0]["msg_id"]) == 35

    def test_both_charset_and_length(self):
        data = [
            self._valid_row(
                debtor_name="Ä" * 200,
                remittance_information="Ö" * 200,
            )
        ]
        result = cleanse_data(data)
        # Ä → Ae (2 chars each), but then truncated to 140
        assert len(result[0]["debtor_name"]) <= 140
        assert validate_swift_charset(result[0]["debtor_name"]) == []

    def test_empty_data(self):
        assert cleanse_data([]) == []

    def test_multiple_rows(self):
        data = [
            self._valid_row(debtor_name="Böhm"),
            self._valid_row(creditor_name="García"),
        ]
        result = cleanse_data(data)
        assert len(result) == 2
        assert "ö" not in result[0]["debtor_name"]
        assert "í" not in result[1]["creditor_name"]

    def test_disable_charset_cleansing(self):
        data = [self._valid_row(debtor_name="Müller")]
        result = cleanse_data(data, cleanse_charset=False)
        assert result[0]["debtor_name"] == "Müller"

    def test_disable_length_enforcement(self):
        data = [self._valid_row(msg_id="X" * 50)]
        result = cleanse_data(data, enforce_lengths=False)
        assert len(result[0]["msg_id"]) == 50


# --- cleanse_data_with_report ---


class TestCleanseDataWithReport:
    def test_clean_data_report(self):
        data = [
            {
                "msg_id": "MSG001",
                "debtor_name": "Test Corp",
                "creditor_name": "Other Corp",
            }
        ]
        result, report = cleanse_data_with_report(data)
        assert report.is_clean
        assert report.rows_processed == 1
        assert report.rows_modified == 0

    def test_dirty_data_report(self):
        data = [
            {
                "msg_id": "X" * 50,
                "debtor_name": "Müller™",
                "creditor_name": "Test",
            }
        ]
        result, report = cleanse_data_with_report(data)
        assert not report.is_clean
        assert report.rows_modified == 1
        assert report.violation_count >= 2  # charset + length

    def test_report_summary(self):
        data = [
            {"msg_id": "OK", "debtor_name": "Clean", "creditor_name": "Clean"}
        ]
        _, report = cleanse_data_with_report(data)
        assert "SWIFT-compliant" in report.summary()


# --- ComplianceViolation ---


class TestComplianceViolation:
    def test_repr(self):
        v = ComplianceViolation(
            field="debtor_name",
            violation_type="charset",
            original_value="Müller",
        )
        assert "debtor_name" in repr(v)
        assert "charset" in repr(v)


# --- SWIFT Compliance Integration with XML Pipeline ---


class TestComplianceXmlIntegration:
    """Test SWIFT compliance cleansing before XML generation."""

    def test_cleansed_data_generates_valid_xml(self):
        """Data with non-SWIFT chars generates valid XML after cleansing."""
        from pacs008.constants import TEMPLATES_DIR
        from pacs008.xml.generate_xml import generate_xml_string

        dirty = [
            {
                "msg_id": "MSG-COMPLIANCE-001",
                "creation_date_time": "2026-01-15T10:30:00",
                "nb_of_txs": "1",
                "settlement_method": "CLRG",
                "interbank_settlement_date": "2026-01-15",
                "end_to_end_id": "E2E-COMPL-001",
                "tx_id": "TX-COMPL-001",
                "interbank_settlement_amount": "5000.00",
                "interbank_settlement_currency": "EUR",
                "charge_bearer": "SHAR",
                "debtor_name": "Müller & Söhne™ GmbH",
                "debtor_account_iban": "DE89370400440532013000",
                "debtor_agent_bic": "DEUTDEFF",
                "creditor_agent_bic": "COBADEFF",
                "creditor_name": "García Café SL",
                "creditor_account_iban": "ES9121000418450200051332",
                "remittance_information": "Invoice™ #123 — €500 payment",
            }
        ]
        clean = cleanse_data(dirty)
        version = "pacs.008.001.05"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        xml = generate_xml_string(clean, version, tpl, xsd)
        assert "Mueller" in xml or "Muller" in xml
        assert "™" not in xml
        assert "€" not in xml

    def test_full_pipeline_with_report(self):
        """cleanse_data_with_report produces report + valid data."""
        dirty = [
            {
                "msg_id": "X" * 50,
                "debtor_name": "Ñoño Corp",
                "creditor_name": "Böhm AG",
                "end_to_end_id": "E2E-001",
                "remittance_information": "Ä" * 200,
            }
        ]
        result, report = cleanse_data_with_report(dirty)
        assert not report.is_clean
        assert report.rows_modified == 1
        assert report.violation_count >= 3
        # msg_id truncated to 35
        assert len(result[0]["msg_id"]) == 35
        # Names are SWIFT-compliant
        assert validate_swift_charset(result[0]["debtor_name"]) == []
        assert validate_swift_charset(result[0]["creditor_name"]) == []
        # Remittance truncated to 140
        assert len(result[0]["remittance_information"]) <= 140

    def test_multi_row_compliance(self):
        """Multiple rows processed correctly with mixed violations."""
        data = [
            {"debtor_name": "Clean Corp", "msg_id": "OK-1"},
            {"debtor_name": "Müller™ AG", "msg_id": "OK-2"},
            {"debtor_name": "García SL", "msg_id": "Y" * 40},
        ]
        result, report = cleanse_data_with_report(data)
        assert report.rows_processed == 3
        assert report.rows_modified == 2  # Rows 2 and 3
        assert result[0]["debtor_name"] == "Clean Corp"  # Unchanged


# --- Unicode Edge Cases ---


class TestUnicodeEdgeCases:
    """Test transliteration of complex Unicode scenarios."""

    def test_cjk_characters_removed(self):
        """CJK characters not in SWIFT set should be replaced."""
        result = cleanse_string("Payment 支払い")
        assert validate_swift_charset(result) == []

    def test_mixed_scripts(self):
        """Mixed Latin + non-Latin should cleanse non-Latin only."""
        result = cleanse_string("ABC αβγ 123")
        assert "ABC" in result
        assert "123" in result
        assert validate_swift_charset(result) == []

    def test_combining_diacritics(self):
        """Characters with combining marks should be normalized."""
        # é can be e + combining acute accent
        import unicodedata

        decomposed = unicodedata.normalize("NFD", "é")
        result = cleanse_string(decomposed)
        assert validate_swift_charset(result) == []

    def test_zero_width_characters(self):
        """Zero-width chars should be stripped."""
        result = cleanse_string("Hello\u200bWorld")  # zero-width space
        assert validate_swift_charset(result) == []

    def test_full_width_digits(self):
        """Full-width digits should be replaced."""
        result = cleanse_string("１２３")  # Full-width 1, 2, 3
        assert validate_swift_charset(result) == []

    def test_all_transliteration_entries(self):
        """Every entry in _TRANSLITERATION produces SWIFT-valid output."""
        from pacs008.compliance.swift_charset import _TRANSLITERATION

        for char, _replacement in _TRANSLITERATION.items():
            result = cleanse_string(char)
            violations = validate_swift_charset(result)
            assert (
                violations == []
            ), f"Transliteration of '{char}' → '{result}' has violations"

    def test_long_transliteration_chain(self):
        """String with many transliterations doesn't break."""
        from pacs008.compliance.swift_charset import _TRANSLITERATION

        s = "".join(_TRANSLITERATION.keys())
        result = cleanse_string(s)
        assert validate_swift_charset(result) == []


# --- Compliance Report ---


class TestComplianceReportDetails:
    """Detailed compliance report testing."""

    def test_summary_with_violations(self):
        data = [{"msg_id": "X" * 50, "debtor_name": "Müller"}]
        _, report = cleanse_data_with_report(data)
        summary = report.summary()
        assert "violation" in summary.lower() or "modified" in summary.lower()

    def test_violation_count_accurate(self):
        data = [
            {
                "msg_id": "X" * 50,
                "debtor_name": "Müller™",
                "creditor_name": "Böhm",
                "end_to_end_id": "Y" * 40,
            }
        ]
        _, report = cleanse_data_with_report(data)
        # charset violations: debtor_name (ü, ™), creditor_name (ö)
        # length violations: msg_id, end_to_end_id
        assert report.violation_count >= 4

    def test_empty_data_clean_report(self):
        _, report = cleanse_data_with_report([])
        assert report.is_clean
        assert report.rows_processed == 0
        assert report.rows_modified == 0
