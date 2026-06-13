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

"""Tests for pacs008.standards.address — November 2026 cliff tooling."""

from __future__ import annotations

from datetime import date

import pytest

from pacs008.standards.address import (
    NOV_2026_CLIFF,
    AddressClassification,
    AddressPolicy,
    AddressValidationError,
    PostalAddress,
    Severity,
    from_unstructured,
    validate_addresses,
)

# ---------------------------------------------------------------------------
# PostalAddress construction & basic invariants
# ---------------------------------------------------------------------------


class TestPostalAddressConstruction:
    def test_empty_address_is_valid(self):
        addr = PostalAddress()
        assert addr.ctry is None
        assert addr.adr_line == ()
        assert not addr.has_structured_fields

    def test_structured_fields_detected(self):
        addr = PostalAddress(strt_nm="High Street", twn_nm="London", ctry="GB")
        assert addr.has_structured_fields

    def test_country_must_be_iso_3166_1_alpha_2(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            PostalAddress(ctry="UK")  # UK is not ISO; GB is

    def test_country_must_be_uppercase(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            PostalAddress(ctry="gb")

    def test_country_must_be_two_letters(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            PostalAddress(ctry="GBR")

    def test_adr_line_accepts_list_input(self):
        addr = PostalAddress(adr_line=["Line 1", "Line 2"])
        assert addr.adr_line == ("Line 1", "Line 2")

    def test_adr_line_max_seven(self):
        addr = PostalAddress(adr_line=tuple(f"L{i}" for i in range(7)))
        assert len(addr.adr_line) == 7

    def test_adr_line_eight_rejected(self):
        with pytest.raises(ValueError, match="7 occurrences"):
            PostalAddress(adr_line=tuple(f"L{i}" for i in range(8)))

    def test_adr_line_70_char_limit(self):
        with pytest.raises(ValueError, match="70-char max"):
            PostalAddress(adr_line=("x" * 71,))

    def test_adr_line_must_be_strings(self):
        with pytest.raises(TypeError, match="must be str"):
            PostalAddress(adr_line=(123,))  # type: ignore[arg-type]

    def test_twn_nm_35_char_limit(self):
        with pytest.raises(ValueError, match="35-char ISO 20022 max"):
            PostalAddress(twn_nm="x" * 36)

    def test_strt_nm_70_char_limit(self):
        with pytest.raises(ValueError, match="70-char ISO 20022 max"):
            PostalAddress(strt_nm="x" * 71)

    def test_bldg_nb_16_char_limit(self):
        with pytest.raises(ValueError, match="16-char ISO 20022 max"):
            PostalAddress(bldg_nb="x" * 17)

    def test_pst_cd_16_char_limit(self):
        with pytest.raises(ValueError, match="16-char ISO 20022 max"):
            PostalAddress(pst_cd="x" * 17)


# ---------------------------------------------------------------------------
# Classification (the core of the Nov 2026 cliff logic)
# ---------------------------------------------------------------------------


class TestAddressClassification:
    def test_structured_requires_twn_ctry_no_adr_line(self):
        addr = PostalAddress(
            strt_nm="High Street",
            bldg_nb="42",
            pst_cd="SW1A 1AA",
            twn_nm="London",
            ctry="GB",
        )
        assert addr.classify() is AddressClassification.STRUCTURED
        assert addr.is_structured()
        assert not addr.is_hybrid()
        assert not addr.is_unstructured()

    def test_hybrid_is_twn_ctry_plus_one_adr_line(self):
        addr = PostalAddress(
            twn_nm="London",
            ctry="GB",
            adr_line=("42 High Street",),
        )
        assert addr.classify() is AddressClassification.HYBRID
        assert addr.is_hybrid()

    def test_hybrid_is_twn_ctry_plus_two_adr_lines(self):
        addr = PostalAddress(
            twn_nm="London",
            ctry="GB",
            adr_line=("42 High Street", "Suite 1"),
        )
        assert addr.is_hybrid()

    def test_three_adr_lines_with_twn_ctry_is_unstructured(self):
        # CBPR+ UG2026 caps hybrid AdrLine at 2; beyond that, the
        # combination is treated as unstructured for cliff purposes.
        addr = PostalAddress(
            twn_nm="London",
            ctry="GB",
            adr_line=("L1", "L2", "L3"),
        )
        assert addr.is_unstructured()

    def test_unstructured_adr_line_only(self):
        addr = PostalAddress(adr_line=("42 High Street", "London SW1A 1AA"))
        assert addr.is_unstructured()

    def test_unstructured_twn_no_ctry(self):
        # Missing ctry — falls to unstructured per the classifier.
        addr = PostalAddress(twn_nm="London")
        assert addr.is_unstructured()

    def test_unstructured_ctry_no_twn(self):
        addr = PostalAddress(ctry="GB")
        assert addr.is_unstructured()


# ---------------------------------------------------------------------------
# AddressPolicy validation
# ---------------------------------------------------------------------------


_PRE_CLIFF = date(2026, 11, 13)
_POST_CLIFF = date(2026, 11, 15)


class TestAddressPolicy:
    def test_unstructured_ok_accepts_anything(self):
        for addr in (
            PostalAddress(adr_line=("foo",)),
            PostalAddress(twn_nm="London", ctry="GB"),
            PostalAddress(
                twn_nm="London", ctry="GB", adr_line=("42 High Street",)
            ),
        ):
            assert addr.validate(AddressPolicy.UNSTRUCTURED_OK) is None

    def test_structured_only_rejects_hybrid(self):
        addr = PostalAddress(
            twn_nm="London", ctry="GB", adr_line=("42 High Street",)
        )
        reason = addr.validate(AddressPolicy.STRUCTURED_ONLY)
        assert reason is not None
        assert "STRUCTURED_ONLY" in reason
        assert "hybrid" in reason

    def test_structured_only_rejects_unstructured(self):
        addr = PostalAddress(adr_line=("foo",))
        reason = addr.validate(AddressPolicy.STRUCTURED_ONLY)
        assert reason is not None
        assert "unstructured" in reason

    def test_structured_only_accepts_structured(self):
        addr = PostalAddress(strt_nm="High Street", twn_nm="London", ctry="GB")
        assert addr.validate(AddressPolicy.STRUCTURED_ONLY) is None

    def test_hybrid_or_structured_accepts_structured(self):
        addr = PostalAddress(strt_nm="High Street", twn_nm="London", ctry="GB")
        assert addr.validate(AddressPolicy.HYBRID_OR_STRUCTURED) is None

    def test_hybrid_or_structured_accepts_hybrid(self):
        addr = PostalAddress(
            twn_nm="London", ctry="GB", adr_line=("42 High Street",)
        )
        assert addr.validate(AddressPolicy.HYBRID_OR_STRUCTURED) is None

    def test_hybrid_or_structured_rejects_unstructured_pre_cliff(self):
        addr = PostalAddress(adr_line=("42 High Street, London SW1A 1AA",))
        reason = addr.validate(
            AddressPolicy.HYBRID_OR_STRUCTURED, today=_PRE_CLIFF
        )
        assert reason is not None
        assert "CBPR+ UG2026" in reason
        assert NOV_2026_CLIFF.isoformat() in reason
        assert "in force from" in reason

    def test_hybrid_or_structured_rejects_unstructured_post_cliff(self):
        addr = PostalAddress(adr_line=("42 High Street, London SW1A 1AA",))
        reason = addr.validate(
            AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert reason is not None
        assert "in force since" in reason

    def test_validate_uses_today_when_no_date_provided(self):
        # Just ensure the no-arg path doesn't crash and follows policy.
        addr = PostalAddress(adr_line=("foo",))
        assert addr.validate(AddressPolicy.HYBRID_OR_STRUCTURED) is not None


# ---------------------------------------------------------------------------
# from_unstructured: country-aware heuristics
# ---------------------------------------------------------------------------


class TestFromUnstructuredGB:
    def test_postcode_alone_on_last_line(self):
        addr = from_unstructured(
            ["42 High Street", "London", "SW1A 1AA"], "GB"
        )
        assert addr.pst_cd == "SW1A 1AA"
        assert addr.twn_nm == "London"
        assert addr.ctry == "GB"
        assert addr.is_hybrid()

    def test_town_and_postcode_on_same_line(self):
        addr = from_unstructured(["42 High Street", "London SW1A 1AA"], "GB")
        assert addr.pst_cd == "SW1A 1AA"
        assert addr.twn_nm == "London"

    def test_lowercase_postcode_normalised(self):
        addr = from_unstructured(["London sw1a 1aa"], "GB")
        assert addr.pst_cd == "SW1A 1AA"

    def test_no_postcode_falls_back_to_last_line(self):
        addr = from_unstructured(["42 High Street", "Townless"], "GB")
        assert addr.twn_nm == "Townless"
        assert addr.pst_cd is None


class TestFromUnstructuredUS:
    def test_city_state_zip_pattern(self):
        addr = from_unstructured(
            ["1 Infinite Loop", "Cupertino, CA 95014"], "US"
        )
        assert addr.pst_cd == "95014"
        assert addr.twn_nm == "Cupertino"
        assert addr.ctry_sub_dvsn == "CA"
        assert addr.ctry == "US"
        assert addr.is_hybrid() or addr.is_structured()

    def test_zip_plus_four(self):
        addr = from_unstructured(
            ["1600 Pennsylvania Ave NW", "Washington, DC 20500-0003"], "US"
        )
        assert addr.pst_cd == "20500-0003"
        assert addr.ctry_sub_dvsn == "DC"

    def test_invalid_state_falls_back(self):
        addr = from_unstructured(
            ["1 Test Street", "Smalltown, ZZ 12345"], "US"
        )
        # ZZ is not a valid state — heuristic falls through to last-line
        assert addr.ctry_sub_dvsn is None


class TestFromUnstructuredDE:
    def test_plz_ort_pattern(self):
        addr = from_unstructured(["Friedrichstraße 100", "10117 Berlin"], "DE")
        assert addr.pst_cd == "10117"
        assert addr.twn_nm == "Berlin"
        assert addr.ctry == "DE"


class TestFromUnstructuredFR:
    def test_code_postal_ville(self):
        addr = from_unstructured(["1 Rue de la Paix", "75001 Paris"], "FR")
        assert addr.pst_cd == "75001"
        assert addr.twn_nm == "Paris"
        assert addr.ctry == "FR"


class TestFromUnstructuredJP:
    def test_japanese_postcode_with_marker(self):
        addr = from_unstructured(["1-1 Chiyoda", "〒100-0001 Tokyo"], "JP")
        assert addr.pst_cd == "100-0001"
        assert addr.twn_nm == "Tokyo"
        assert addr.ctry == "JP"

    def test_japanese_postcode_without_marker(self):
        addr = from_unstructured(["Tokyo 100-0001"], "JP")
        assert addr.pst_cd == "100-0001"


class TestFromUnstructuredFallback:
    def test_unknown_country_passes_through(self):
        addr = from_unstructured(["Street 1", "City", "Region"], "IT")
        assert addr.ctry == "IT"
        assert addr.twn_nm == "Region"  # last line as best-effort town

    def test_empty_input_returns_country_only(self):
        addr = from_unstructured([], "GB")
        assert addr.ctry == "GB"
        assert addr.twn_nm is None
        assert addr.adr_line == ()

    def test_whitespace_only_lines_skipped(self):
        addr = from_unstructured(["   ", "", "London", "SW1A 1AA"], "GB")
        assert addr.pst_cd == "SW1A 1AA"
        assert addr.twn_nm == "London"

    def test_invalid_country_hint_rejected(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            from_unstructured(["foo"], "ZZZ")

    def test_lowercase_country_hint_rejected(self):
        with pytest.raises(ValueError, match="ISO 3166-1 alpha-2"):
            from_unstructured(["foo"], "gb")


class TestFromUnstructuredAdrLineCap:
    def test_hybrid_output_caps_adr_line_at_two(self):
        # 6 leading lines; only the last becomes town, the prior 5 must
        # be packed into at most 2 AdrLine entries.
        addr = from_unstructured(
            ["L1", "L2", "L3", "L4", "L5", "London"], "GB"
        )
        assert len(addr.adr_line) <= 2

    def test_long_adr_line_truncated_to_70_chars(self):
        long_line = "x" * 100
        addr = from_unstructured([long_line, "London SW1A 1AA"], "GB")
        for line in addr.adr_line:
            assert len(line) <= 70


# ---------------------------------------------------------------------------
# validate_addresses pipeline helper
# ---------------------------------------------------------------------------


def _good_structured(party: str) -> dict[str, str]:
    return {
        f"{party}_address_strt_nm": "High Street",
        f"{party}_address_bldg_nb": "42",
        f"{party}_address_pst_cd": "SW1A 1AA",
        f"{party}_address_twn_nm": "London",
        f"{party}_address_ctry": "GB",
    }


def _bad_unstructured(party: str) -> dict[str, str]:
    return {
        f"{party}_address_adr_line_0": "42 High Street",
        f"{party}_address_adr_line_1": "London SW1A 1AA",
    }


class TestValidateAddresses:
    def test_empty_input_returns_empty(self):
        assert validate_addresses([], AddressPolicy.HYBRID_OR_STRUCTURED) == []

    def test_no_address_columns_skipped(self):
        rows = [{"debtor_name": "Bob", "creditor_name": "Alice"}]
        assert (
            validate_addresses(rows, AddressPolicy.HYBRID_OR_STRUCTURED) == []
        )

    def test_unstructured_ok_lets_unstructured_pass(self):
        rows = [_bad_unstructured("debtor")]
        assert validate_addresses(rows, AddressPolicy.UNSTRUCTURED_OK) == []

    def test_unstructured_debtor_blocks_under_cliff_policy(self):
        rows = [_bad_unstructured("debtor")]
        errors = validate_addresses(
            rows, AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert len(errors) == 1
        err = errors[0]
        assert err.row == 0
        assert err.party == "debtor"
        assert err.severity is Severity.BLOCK
        assert err.classification is AddressClassification.UNSTRUCTURED

    def test_mixed_row_reports_only_offending_party(self):
        row = {**_good_structured("debtor"), **_bad_unstructured("creditor")}
        errors = validate_addresses(
            [row], AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert [e.party for e in errors] == ["creditor"]

    def test_agent_addresses_validated(self):
        rows = [_bad_unstructured("debtor_agent")]
        errors = validate_addresses(
            rows, AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert errors and errors[0].party == "debtor_agent"

    def test_ultimate_party_addresses_validated(self):
        rows = [_bad_unstructured("ultimate_creditor")]
        errors = validate_addresses(
            rows, AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert errors and errors[0].party == "ultimate_creditor"

    def test_multi_row_returns_per_row_errors(self):
        rows = [
            _bad_unstructured("debtor"),
            _good_structured("debtor"),
            _bad_unstructured("debtor"),
        ]
        errors = validate_addresses(
            rows, AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        assert sorted(e.row for e in errors) == [0, 2]

    def test_blank_string_treated_as_missing(self):
        # Empty-string CSV cells should be treated as missing, not as
        # populating the field with a zero-length string.
        rows = [
            {
                "debtor_address_strt_nm": "",
                "debtor_address_twn_nm": "London",
                "debtor_address_ctry": "GB",
            }
        ]
        errors = validate_addresses(
            rows, AddressPolicy.HYBRID_OR_STRUCTURED, today=_POST_CLIFF
        )
        # twn_nm + ctry alone with no AdrLine — STRUCTURED (no AdrLine).
        # Should pass.
        assert errors == []


# ---------------------------------------------------------------------------
# AddressValidationError dataclass surface
# ---------------------------------------------------------------------------


class TestAddressValidationError:
    def test_is_hashable_and_immutable(self):
        err = AddressValidationError(
            row=0,
            party="debtor",
            severity=Severity.BLOCK,
            message="x",
            classification=AddressClassification.UNSTRUCTURED,
        )
        # frozen dataclass — hashable, settable attrs blocked
        hash(err)
        with pytest.raises(Exception):
            err.row = 1  # type: ignore[misc]
