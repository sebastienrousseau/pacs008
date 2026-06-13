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

"""Tests for the Block F additions to SWIFT charset handling:

- ``anyascii`` fallback for non-Latin scripts.
- Space replacement (was period) for unmappable characters.
- ``policy="reject"`` mode.
- Per-scheme charset (X vs Z), with FedwireProfile overriding to Z.
"""

from __future__ import annotations

import pytest

from pacs008.compliance.swift_charset import (
    SWIFT_X_CHARSET,
    SWIFT_Z_CHARSET,
    cleanse_data,
    cleanse_data_with_report,
    cleanse_string,
    validate_swift_charset,
)
from pacs008.exceptions import PaymentValidationError
from pacs008.profiles import (
    CBPRPlusProfile,
    FedwireProfile,
    GenericProfile,
)


# ---------------------------------------------------------------------------
# F1: non-Latin scripts via anyascii
# ---------------------------------------------------------------------------


class TestNonLatinTransliteration:
    def test_cyrillic_becomes_latin(self):
        # Was previously destroyed to dots; anyascii gives a usable
        # transliteration.
        assert cleanse_string("Москва") == "Moskva"

    def test_cjk_becomes_pinyin_like(self):
        # Pre-Block-F: every CJK char became "."; now anyascii returns
        # a Pinyin/Wade-Giles-ish romanisation.
        result = cleanse_string("東京")
        assert result and all(c in SWIFT_X_CHARSET for c in result)
        assert "Dong" in result  # 東 → Dong

    def test_arabic_becomes_latin(self):
        result = cleanse_string("مصر")  # Egypt
        assert result and all(c in SWIFT_X_CHARSET for c in result)

    def test_greek_becomes_latin(self):
        # Αθήνα -> Athina (or similar)
        result = cleanse_string("Αθήνα")
        assert result and all(c in SWIFT_X_CHARSET for c in result)
        assert "Ath" in result

    def test_hebrew_becomes_latin(self):
        # Tel Aviv in Hebrew
        result = cleanse_string("תל אביב")
        assert result and all(c in SWIFT_X_CHARSET for c in result)

    def test_devanagari_becomes_latin(self):
        # Mumbai in Devanagari
        result = cleanse_string("मुंबई")
        assert result and all(c in SWIFT_X_CHARSET for c in result)


# ---------------------------------------------------------------------------
# F1 retained: explicit map still works
# ---------------------------------------------------------------------------


class TestExplicitMapStillApplies:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("ä", "ae"),
            ("ö", "oe"),
            ("ü", "ue"),
            ("ß", "ss"),
            ("é", "e"),
            ("ñ", "n"),
        ],
    )
    def test_common_german_romance_letters(self, raw, expected):
        assert cleanse_string(raw) == expected


# ---------------------------------------------------------------------------
# F2: space (not period) for unmappable chars
# ---------------------------------------------------------------------------


class TestSpaceFallback:
    def test_truly_unmappable_char_becomes_space(self):
        # Use a private-use Unicode codepoint — anyascii returns ""
        # for these, so the space fallback should fire.
        private_use_char = ""
        result = cleanse_string(f"A{private_use_char}B")
        assert result == "A B"

    def test_multiple_spaces_collapsed(self):
        assert cleanse_string("Hello  World    Foo") == "Hello World Foo"

    def test_leading_trailing_spaces_preserved(self):
        # We collapse runs but don't strip — caller chooses.
        assert cleanse_string(" Hello ") == " Hello "

    def test_crlf_not_collapsed(self):
        # \r and \n are valid SWIFT-X characters and should pass through
        # unchanged even with the new collapse rule.
        assert cleanse_string("Line1\nLine2") == "Line1\nLine2"
        assert cleanse_string("Line1\r\nLine2") == "Line1\r\nLine2"


# ---------------------------------------------------------------------------
# F2: reject policy
# ---------------------------------------------------------------------------


class TestRejectPolicy:
    def test_reject_passes_clean_string(self):
        assert (
            cleanse_string("Plain ASCII text", policy="reject")
            == "Plain ASCII text"
        )

    def test_reject_raises_on_first_offender(self):
        with pytest.raises(PaymentValidationError) as excinfo:
            cleanse_string("café", policy="reject")
        msg = str(excinfo.value)
        assert "Position 3" in msg  # 'é' is at index 3
        assert "U+00E9" in msg  # codepoint hint

    def test_reject_raises_on_cyrillic(self):
        with pytest.raises(PaymentValidationError):
            cleanse_string("Москва", policy="reject")

    def test_reject_policy_respects_charset(self):
        # Z-charset allows é; reject should NOT raise.
        assert (
            cleanse_string("café", charset=SWIFT_Z_CHARSET, policy="reject")
            == "café"
        )

    def test_invalid_policy_raises_value_error(self):
        with pytest.raises(ValueError, match="cleanse.*reject"):
            cleanse_string("foo", policy="warn")


# ---------------------------------------------------------------------------
# F3: SWIFT Z charset vs X
# ---------------------------------------------------------------------------


class TestZCharsetBehaviour:
    def test_z_is_superset_of_x(self):
        assert SWIFT_X_CHARSET.issubset(SWIFT_Z_CHARSET)
        assert len(SWIFT_Z_CHARSET) > len(SWIFT_X_CHARSET)

    def test_z_accepts_accented_latin(self):
        for ch in "éàüöñçßØ":
            assert ch in SWIFT_Z_CHARSET, f"{ch!r} should be in Z"

    def test_z_accepts_extra_ascii_printables(self):
        # The extra punctuation that Z permits.
        for ch in "!@#$%&_=":
            assert ch in SWIFT_Z_CHARSET, f"{ch!r} should be in Z"

    def test_x_rejects_accented_latin(self):
        for ch in "éàüöñç":
            assert ch not in SWIFT_X_CHARSET

    def test_cleanse_to_z_preserves_accents(self):
        assert cleanse_string("café", charset=SWIFT_Z_CHARSET) == "café"
        assert cleanse_string("Müller", charset=SWIFT_Z_CHARSET) == "Müller"

    def test_cleanse_to_z_still_transliterates_non_latin(self):
        # Cyrillic isn't in Z either — should still go through anyascii.
        assert cleanse_string("Москва", charset=SWIFT_Z_CHARSET) == "Moskva"


# ---------------------------------------------------------------------------
# F3: charset property on profiles
# ---------------------------------------------------------------------------


class TestProfileCharset:
    def test_generic_uses_x(self):
        assert GenericProfile().charset is SWIFT_X_CHARSET

    def test_cbpr_plus_uses_x(self):
        assert CBPRPlusProfile().charset is SWIFT_X_CHARSET

    def test_fedwire_uses_z(self):
        assert FedwireProfile().charset is SWIFT_Z_CHARSET

    def test_cleansing_via_profile_charset(self):
        # Fedwire passes through é; CBPR+ strips the accent.
        for profile_cls, expected in [
            (CBPRPlusProfile, "cafe"),
            (FedwireProfile, "café"),
        ]:
            profile = profile_cls()
            result = cleanse_string("café", charset=profile.charset)
            assert result == expected


# ---------------------------------------------------------------------------
# Integration: cleanse_data + cleanse_data_with_report with new params
# ---------------------------------------------------------------------------


class TestCleanseDataNewParams:
    def test_cleanse_data_accepts_charset(self):
        rows = [{"debtor_name": "café Müller"}]
        result = cleanse_data(rows, charset=SWIFT_Z_CHARSET)
        # Z passes both é and ü through.
        assert result[0]["debtor_name"] == "café Müller"

    def test_cleanse_data_with_x_strips_accents(self):
        rows = [{"debtor_name": "café Müller"}]
        result = cleanse_data(rows, charset=SWIFT_X_CHARSET)
        assert result[0]["debtor_name"] == "cafe Mueller"

    def test_cleanse_data_with_report_includes_violation(self):
        rows = [{"debtor_name": "Москва"}]
        cleansed, report = cleanse_data_with_report(rows)
        assert cleansed[0]["debtor_name"] == "Moskva"
        assert report.violation_count == 1
        assert report.violations[0].field == "debtor_name"

    def test_cleanse_data_reject_policy_raises(self):
        rows = [{"debtor_name": "café"}]
        with pytest.raises(PaymentValidationError):
            cleanse_data(rows, policy="reject")


# ---------------------------------------------------------------------------
# validate_swift_charset with custom charset
# ---------------------------------------------------------------------------


class TestValidateCharsetWithZ:
    def test_x_validation_flags_accented_chars(self):
        violations = validate_swift_charset("café")
        assert len(violations) == 1
        assert violations[0] == (3, "é")

    def test_z_validation_accepts_accented_chars(self):
        violations = validate_swift_charset("café", charset=SWIFT_Z_CHARSET)
        assert violations == []
