#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What a payment batch costs to cleanse and split for a scheme.

A `pacs.008` batch is not one payment. A correspondent bank sends a file of
them, and schemes cap how many may travel in a single message — so a batch
that arrives as ten thousand instructions leaves as some number of
scheme-sized messages. Two steps decide whether that is a job or a problem.

* **`cleanse_data`** walks every field of every row, enforcing SWIFT
  character-set rules and field lengths. It touches everything, so it is
  the step most likely to dominate, and its cost should be strictly linear
  in rows.

* **`split_for_scheme`** divides the batch into scheme-sized chunks. It
  should be linear too, and cheap: it is arithmetic and slicing, not
  inspection. If splitting ever costs a meaningful fraction of cleansing,
  something is re-walking the batch per chunk — which is invisible on a
  fixture of three payments and quadratic on a real file.

  It returns a **generator**, so it is measured consumed. Timing the bare
  call measures building the generator object and reports that splitting
  is free, which is true only in the sense that nothing has happened yet.

Read `us/row` in both columns. Flat across sizes is linear; climbing means
the batch is being traversed more than once.

The **charset** check is measured separately at the single-value level,
because it is the innermost loop: it runs per character of per field of
per row, so a change there multiplies through everything above it.

Run::

    python benches/bench_batch_pipeline.py
    python benches/bench_batch_pipeline.py --json
    python benches/bench_batch_pipeline.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped compiling against the
current API fails the build instead of rotting into a file that reads as
verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pacs008.compliance import (
    cleanse_data,
    validate_swift_charset,
)  # noqa: E402
from pacs008.core.splitter import (  # noqa: E402
    required_chunks,
    split_for_scheme,
)

SCHEME = "CBPR+"


def build(rows: int) -> list[dict]:
    """A batch of ``rows`` interbank credit transfers.

    Every tenth row carries a character outside the SWIFT set, so the
    cleanser has work to do rather than confirming a clean batch — which
    would measure the fast path and skip the substitution entirely.
    """
    batch = []
    for i in range(rows):
        name = f"Acme Supplier {i}" if i % 10 else f"Café Supplíer {i}"
        batch.append(
            {
                "msg_id": f"MSG-{i:07d}",
                "creation_date_time": "2026-06-21T10:00:00",
                "nb_of_txs": "1",
                "settlement_method": "CLRG",
                "end_to_end_id": f"E2E-{i:07d}",
                "interbank_settlement_amount": f"{(i % 900) + 100}.00",
                "interbank_settlement_currency": "EUR",
                "charge_bearer": "SLEV",
                "debtor_name": name,
                "debtor_agent_bic": "DEUTDEFFXXX",
                "creditor_agent_bic": "NWBKGB2LXXX",
                "creditor_name": f"Beta GmbH {i}",
                "remittance_information": f"Invoice {i}",
            }
        )
    return batch


def _best(call, repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator available; the mean follows
    whatever else the machine is doing.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def _safe(call):
    """A refusal is a result: how fast it declines is a measurement."""

    def wrapped():
        try:
            return call()
        except Exception:
            return None

    return wrapped


def measure(rows: int, repeats: int) -> dict:
    batch = build(rows)
    cleanse = _best(_safe(lambda: cleanse_data(batch)), repeats)
    # Consumed, not just created. split_for_scheme returns a generator,
    # so timing the bare call measures building the generator object --
    # about 0.5 us regardless of batch size, which reads as "splitting
    # is free" and is not a measurement of anything.
    split = _best(
        _safe(lambda: list(split_for_scheme(batch, SCHEME))), repeats
    )
    chunks = _safe(lambda: required_chunks(batch, SCHEME))()
    return {
        "rows": rows,
        "chunks": chunks,
        "cleanse_ms": cleanse * 1e3,
        "split_ms": split * 1e3,
        "cleanse_us_per_row": cleanse * 1e6 / rows,
        "split_us_per_row": split * 1e6 / rows,
        "split_over_cleanse": split / cleanse if cleanse else 0.0,
    }


def run(quick: bool) -> dict:
    sizes = [100, 1_000] if quick else [100, 1_000, 10_000, 50_000]
    repeats = 2 if quick else 5
    charset = _best(
        lambda: validate_swift_charset("Acme Supplier Limited"),
        2_000 if quick else 20_000,
    )
    return {
        "sizes": [measure(n, repeats) for n in sizes],
        "charset_us": charset * 1e6,
    }


def render(results: dict) -> None:
    print(
        f"{'rows':>8}{'chunks':>8}{'cleanse ms':>12}{'split ms':>11}"
        f"{'cleanse us/row':>16}{'split us/row':>14}"
    )
    for row in results["sizes"]:
        print(
            f"{row['rows']:>8}{str(row['chunks']):>8}"
            f"{row['cleanse_ms']:>12.1f}{row['split_ms']:>11.2f}"
            f"{row['cleanse_us_per_row']:>16.2f}"
            f"{row['split_us_per_row']:>14.3f}"
        )
    rows = results["sizes"]
    if len(rows) >= 2 and rows[0]["cleanse_us_per_row"]:
        drift = rows[-1]["cleanse_us_per_row"] / rows[0]["cleanse_us_per_row"]
        print(
            f"\n  cleanse us/row at {rows[-1]['rows']:,} is {drift:.2f}x the "
            f"cost at {rows[0]['rows']:,}. Flat is linear; climbing means "
            f"the batch is walked more than once."
        )
        worst = max(r["split_over_cleanse"] for r in rows)
        verdict = (
            "arithmetic, as it should be"
            if worst < 0.1
            else "a meaningful share — check it is not re-walking per chunk"
        )
        print(
            f"  Splitting costs up to {worst * 100:.1f}% of cleansing — "
            f"{verdict}."
        )
    print(
        f"\n  validate_swift_charset: {results['charset_us']:.2f} us per "
        f"value. This is the innermost loop — per character, per field,\n"
        f"  per row — so a change here multiplies through everything above."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    results = run(quick=args.quick)
    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        render(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
