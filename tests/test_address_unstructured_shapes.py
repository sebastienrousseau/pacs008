# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Address shapes the country heuristics have to fall back on.

`from_unstructured` is the function that turns a free-text address into the
structured form the CBPR+ rule requires, and it is the one piece of this package
that has to cope with input nobody validated. Each country parser looks for an
anchor -- a state and ZIP in the US, a postcode in Japan, a postal code and town
on one line on the continent -- and every one of them needs an answer for the
address that does not contain the anchor at all.

Those fallback branches were uncovered. They matter more than the happy paths
they sit beside: an address that matches the pattern was never the problem, and
the whole point of remediation is the one that does not.
"""

from __future__ import annotations

import pytest

from pacs008.standards.address import from_unstructured


class TestUnitedStates:
    def test_town_is_taken_from_the_line_carrying_state_and_zip(self) -> None:
        address = from_unstructured(
            ["1 Broadway", "Cambridge, MA 02139"], country_hint="US"
        )
        assert address.twn_nm == "Cambridge"
        assert address.pst_cd == "02139"
        assert address.ctry_sub_dvsn == "MA"

    def test_state_and_zip_alone_on_a_line_take_the_line_above_as_town(
        self,
    ) -> None:
        # No town on the anchor line, so the parser has to look back a line.
        address = from_unstructured(
            ["1 Broadway", "Cambridge", "MA 02139"], country_hint="US"
        )
        assert address.twn_nm == "Cambridge"
        assert address.pst_cd == "02139"

    def test_no_state_and_zip_at_all_still_produces_an_address(self) -> None:
        # The anchor is absent, which is the case the fallback exists for.
        address = from_unstructured(
            ["1 Broadway", "Somewhere"], country_hint="US"
        )
        assert address.ctry == "US"
        assert address.twn_nm


class TestContinental:
    def test_postal_code_and_town_on_one_line(self) -> None:
        address = from_unstructured(
            ["Hauptstrasse 1", "10115 Berlin"], country_hint="DE"
        )
        assert address.pst_cd == "10115"
        assert address.twn_nm == "Berlin"

    def test_without_a_postal_code_the_last_line_becomes_the_town(
        self,
    ) -> None:
        address = from_unstructured(
            ["Hauptstrasse 1", "Berlin"], country_hint="DE"
        )
        assert address.twn_nm == "Berlin"
        assert address.ctry == "DE"

    def test_france_uses_the_same_shape(self) -> None:
        address = from_unstructured(
            ["1 rue de Rivoli", "75001 Paris"], country_hint="FR"
        )
        assert address.pst_cd == "75001"
        assert address.twn_nm == "Paris"


class TestJapan:
    def test_without_a_recognisable_postcode_the_last_line_is_the_town(
        self,
    ) -> None:
        address = from_unstructured(
            ["1-1 Chiyoda", "Tokyo"], country_hint="JP"
        )
        assert address.twn_nm == "Tokyo"
        assert address.ctry == "JP"


class TestFallback:
    def test_an_unknown_country_still_yields_a_town_and_country(self) -> None:
        # No country-specific parser exists, so the generic path runs.
        address = from_unstructured(
            ["Some street 1", "Some city"], country_hint="ZW"
        )
        assert address.ctry == "ZW"
        assert address.twn_nm

    @pytest.mark.parametrize("country", ["GB", "US", "DE", "FR", "JP", "ZW"])
    def test_a_single_line_is_never_rejected(self, country: str) -> None:
        # One line is the least a caller can supply, and every parser has to
        # return something rather than raise: the finding that the address is
        # inadequate belongs to the linter, not to the parser.
        address = from_unstructured(["Somewhere"], country_hint=country)
        assert address.ctry == country
