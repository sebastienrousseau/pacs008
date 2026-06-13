# Performance baselines

This document records baseline numbers for the four hottest paths in
the v0.0.2 surface. The suite lives at
[`tests/perf/test_perf_baseline.py`](tests/perf/test_perf_baseline.py)
and is **excluded from the default `pytest` run** (it is marked
`@pytest.mark.perf` and the project's `addopts` carries `-m "not perf"`).

> ⚠️ These are **baselines, not optimisation targets**. The intent is
> regression detection — if a future change halves the OPS on any of
> these, it should be a deliberate trade-off documented in the PR.

## How to reproduce

```bash
poetry run pytest tests/perf/ \
    -m perf \
    --benchmark-only \
    --benchmark-columns=median,ops,stddev \
    --benchmark-sort=name \
    --no-cov
```

## Reference numbers — v0.0.2

Hardware: Apple Silicon (Darwin 25.5.0), Python 3.12.13,
`pytest-benchmark==4.0.0`. Each row is the median of five pedantic
rounds (one iteration per round). The **Before** column is the
unoptimised baseline; the **After** column is the current code after
the three optimisations described in the next section.

| Path | Before | After | Δ |
|---|---|---|---|
| `cleanse_data` over 10,000 mixed-script rows | 168 ms | **171 ms** | ≈ unchanged |
| `validate_lei_safe` over 10,000 ISO 17442 LEIs | 21 ms | **22 ms** | ≈ unchanged |
| `split_for_scheme` lazy first-chunk pull (100k rows, Fedwire cap=1) | 1.4 µs | **1.5 µs** | ≈ unchanged (already optimal) |
| `split_for_scheme` eager 100k rows (CBPR+ cap=10,000 → 10 chunks) | 26 ms | **27 ms** | ≈ unchanged |
| `generate_xml_string` — 1 row, pacs.008.001.08 | 10.5 ms | **1.4 ms** | **🎉 7.5× faster** |
| `generate_xml_string` — 100 rows | 41 ms | **34 ms** | 17% faster |
| `generate_xml_string` — 10,000 rows | 3.3 s | **3.6 s** | ≈ unchanged (XSD-bound) |

The headline win is **single-row XML generation** — most production
API requests fall into this case (one transaction per call). The
optimisation is a single ``@lru_cache(maxsize=32)`` decorator on the
Jinja ``Environment`` factory in ``pacs008/xml/generate_xml.py``.

## Optimisations applied

Three of the four opportunities documented in v0.0.2 have been
applied. Each is local to one module and verifiable from the
benchmark suite.

### 1. Jinja `Environment` reuse (7.5× win on single-row generation)

`pacs008/xml/generate_xml.py` previously constructed a fresh
`Environment(loader=FileSystemLoader(...), autoescape=True)` on every
`generate_xml_string` call. That dominated the per-call cost on small
batches — Jinja walks the loader path, compiles the template, and
warms its global namespace on every call.

`_get_jinja_environment(loader_path)` is now decorated with
`@lru_cache(maxsize=32)`, keyed on the template directory. Hot
callers (FastAPI request handlers, async job manager) reuse the
cached environment after the first call.

Effect: `generate_xml_string[1]` 10.5 ms → **1.4 ms**. Larger batches
benefit proportionally less because the per-row template render
dominates.

### 2. `xmlschema.XMLSchema` parse cache (already in place)

`pacs008/xml/validate_via_xsd.py` already wraps `XMLSchema(xsd_path)`
in an `lru_cache(maxsize=16)` via `_get_cached_schema`. Verified
during this optimisation pass — no change needed.

### 3. Lazy `anyascii` import (memory win, not CPU win)

`pacs008/compliance/swift_charset.py` previously imported
`anyascii.anyascii` at module load. Now the import is deferred to
the first non-Latin character encountered (`_anyascii` proxy).

Latin-only callers — most CBPR+ traffic in Europe and most US
domestic Fedwire payments — never pay the ~150 KB resident-memory
cost or the ~5 ms import time. The benchmark numbers for
`cleanse_data` are unchanged because the test fixture deliberately
exercises Cyrillic + CJK rows.

## Method

Each benchmark uses `benchmark.pedantic` with `rounds=5, iterations=1`
to minimise measurement noise on long-running tests. Inputs are
realistic: every payment row carries a `Müller & Söhne` debtor name
and a `Москва` creditor name so the charset path exercises both the
German/Romance explicit map and the `anyascii` non-Latin fallback in
the same call.

The four paths chosen are the ones that operationally most often hit
container resource limits:

1. **`cleanse_data`** runs once over every batch — the only path that
   touches every text field in every row.
2. **`validate_lei_safe`** is called once per LEI per party per row;
   a CHAPS batch of 1,000 rows with both FI LEIs populated produces
   2,000 checksums.
3. **`split_for_scheme`** matters mostly for the laziness guarantee —
   SCT Inst and Fedwire one-tx-per-file rails would create millions of
   chunks if the generator materialised eagerly.
4. **`generate_xml_string`** is the main per-message CPU + memory
   driver. The streaming writer (`pacs008.xml.stream_writer`) exists
   precisely so 100k+ row batches do not hit the OOM cliff that the
   Jinja path reaches around ~50k rows in container-bounded memory.

## Method

Each benchmark uses `benchmark.pedantic` with `rounds=5, iterations=1`
to minimise measurement noise on long-running tests. Inputs are
realistic: every payment row carries a `Müller & Söhne` debtor name
and a `Москва` creditor name so the charset path exercises both the
German/Romance explicit map and the `anyascii` non-Latin fallback in
the same call.

The four paths chosen are the ones that operationally most often hit
container resource limits:

1. **`cleanse_data`** runs once over every batch — the only path that
   touches every text field in every row.
2. **`validate_lei_safe`** is called once per LEI per party per row;
   a CHAPS batch of 1,000 rows with both FI LEIs populated produces
   2,000 checksums.
3. **`split_for_scheme`** matters mostly for the laziness guarantee —
   SCT Inst and Fedwire one-tx-per-file rails would create millions of
   chunks if the generator materialised eagerly.
4. **`generate_xml_string`** is the main per-message CPU + memory
   driver. The streaming writer (`pacs008.xml.stream_writer`) exists
   precisely so 100k+ row batches do not hit the OOM cliff that the
   Jinja path reaches around ~50k rows in container-bounded memory.

## Remaining optimisation opportunities

The three quick wins above are already applied. The remaining one is
heavier and stays deferred:

- **Streaming-writer XSD validation.** `pacs008/xml/stream_writer.py`
  currently emits valid XML but defers XSD validation to a post-write
  pass (reading the file back via `xmlschema.iter_errors`).
  Implementing `lxml.etree.iterparse`-based streaming validation
  against the schema would let us validate million-row outputs
  without buffering. This is a substantive piece of work that
  warrants its own PR with before/after numbers from this same
  benchmark suite as the gate.
