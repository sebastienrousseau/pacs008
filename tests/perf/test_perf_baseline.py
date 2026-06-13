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

"""Performance baselines for the four hottest pacs008 paths.

These tests are marked ``perf`` and skipped by the default test run.
Invoke explicitly with::

    poetry run pytest tests/perf/ -m perf --benchmark-only --no-cov

Each benchmark records median, p95, ops/sec and standard deviation.
``BENCHMARKS.md`` at the repo root carries the headline numbers from
the maintainer's run for regression-tracking.

The four paths chosen are the surfaces most likely to hit container
memory or CPU limits in production:

1. **`cleanse_data`** — character-set cleansing pass, runs once per
   batch. Hot path because every text field is scanned.
2. **`validate_lei_safe`** — ISO 7064 mod-97-10 checksum, runs once
   per LEI per row (up to 6 parties × N rows).
3. **`split_for_scheme`** — laziness target — must not materialise
   all chunks up front for one-tx-per-file rails (Fedwire,
   SCT Inst).
4. **`generate_xml_string`** — the Jinja render path; the main
   driver of per-message CPU + memory.
"""

from __future__ import annotations

import pytest

from pacs008 import generate_xml_string
from pacs008.compliance import cleanse_data
from pacs008.core.splitter import split_for_scheme
from pacs008.validation.lei_validator import validate_lei_safe

pytestmark = pytest.mark.perf

# Real-world reference data — used to stay representative.
_REAL_GLEIS = [
    "HWUPKR0MPOU8FGXBT394",  # Apple Inc.
    "7H6GLXDRUGQFU57RNE97",  # JPMorgan Chase Bank, NA
    "INR2EJN1ERAN0W5ZP974",  # Microsoft Corporation
    "529900T8BM49AURSDO55",  # Bloomberg LP
    "784F5XWPLTWKTBV3E584",  # Goldman Sachs Group, Inc.
    "54930043XZGB27CTOV49",  # Tesla, Inc.
    "9DJT3UXIJIZJI4WXO774",  # Bank of America Corp
    "6SHGI4ZSSLCXXQSBB395",  # Citigroup Inc.
    "PBLD0EJDB5FWOLXP3B76",  # Wells Fargo & Co
]


def _payment_row(i: int) -> dict:
    """Build one realistic payment row for benchmark fixtures."""
    return {
        "msg_id": "BATCH001",
        "creation_date_time": "2026-06-13T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-06-15",
        "end_to_end_id": f"E2E-{i:06d}",
        "tx_id": f"TX-{i:06d}",
        "uetr": f"f47ac10b-58cc-4372-a567-{i:012d}",
        "interbank_settlement_amount": f"{1000 + i}.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": f"Müller & Söhne {i} 東京",  # mixed scripts
        "debtor_account_iban": "DE89370400440532013000",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "BNPAFRPP",
        "creditor_name": f"Москва Industries {i}",
        "creditor_account_iban": "FR7630006000011234567890189",
        "remittance_information": f"Invoice INV-2026-{i:06d} Müller",
    }


# ---------------------------------------------------------------------------
# 1. cleanse_data — SWIFT charset pass over 10,000 mixed-script rows
# ---------------------------------------------------------------------------


class TestCleanseDataPerf:
    def test_cleanse_10k_rows_mixed_scripts(self, benchmark):
        rows = [_payment_row(i) for i in range(10_000)]
        result = benchmark.pedantic(
            cleanse_data, args=(rows,), iterations=1, rounds=5
        )
        assert len(result) == 10_000


# ---------------------------------------------------------------------------
# 2. validate_lei_safe — mod-97-10 checksum on 10,000 LEIs
# ---------------------------------------------------------------------------


class TestLEIValidatorPerf:
    def test_validate_10k_leis(self, benchmark):
        # Cycle through 9 real GLEIs to reach 10k checks.
        leis = (_REAL_GLEIS * (10_000 // len(_REAL_GLEIS) + 1))[:10_000]

        def run() -> int:
            return sum(1 for lei in leis if validate_lei_safe(lei))

        passed = benchmark.pedantic(run, iterations=1, rounds=5)
        assert passed == 10_000


# ---------------------------------------------------------------------------
# 3. split_for_scheme — laziness check on 100,000 rows under Fedwire
# ---------------------------------------------------------------------------


class TestSplitterPerf:
    def test_split_100k_rows_fedwire_pull_first_only(self, benchmark):
        # 100k rows under Fedwire (cap=1) would mean 100k chunks if eager.
        # The generator should pull only the first chunk.
        rows = [_payment_row(i) for i in range(100_000)]

        def pull_first() -> dict:
            gen = split_for_scheme(rows, "fedwire")
            return next(gen)[0]

        first = benchmark.pedantic(pull_first, iterations=1, rounds=10)
        assert first["end_to_end_id"] == "E2E-000000"

    def test_split_100k_rows_cbpr_plus_eager(self, benchmark):
        # CBPR+ cap=10000 → 10 chunks. Materialise all chunks.
        rows = [_payment_row(i) for i in range(100_000)]

        def materialise_all() -> int:
            return sum(1 for _ in split_for_scheme(rows, "cbpr_plus"))

        chunks = benchmark.pedantic(materialise_all, iterations=1, rounds=5)
        assert chunks == 10


# ---------------------------------------------------------------------------
# 4. generate_xml_string — Jinja render path at 1 / 100 / 10,000 rows
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def template_paths():
    """Resolve the pacs.008.001.08 template + XSD paths once per module."""
    import pathlib

    base = (
        pathlib.Path(__file__).parent.parent.parent
        / "pacs008"
        / "templates"
        / "pacs.008.001.08"
    )
    return str(base / "template.xml"), str(base / "pacs.008.001.08.xsd")


class TestGenerateXmlPerf:
    @pytest.mark.parametrize("n_rows", [1, 100, 10_000])
    def test_generate_xml_string(self, benchmark, template_paths, n_rows):
        rows = [_payment_row(i) for i in range(n_rows)]
        template_path, xsd_path = template_paths

        def run() -> int:
            xml = generate_xml_string(
                rows, "pacs.008.001.08", template_path, xsd_path
            )
            return len(xml)

        size = benchmark.pedantic(run, iterations=1, rounds=3)
        # Sanity: bigger batch → bigger output.
        assert size > 0
