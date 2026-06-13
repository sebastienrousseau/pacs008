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
rounds (one iteration per round).

| Path | Median time | Ops/sec | Notes |
|---|---|---|---|
| `cleanse_data` over 10,000 mixed-script rows | **168 ms** | ~6 | Cyrillic + CJK + German diacritics; full SWIFT-X transliteration with `anyascii` fallback. ~60,000 rows/sec sustained. |
| `validate_lei_safe` over 10,000 ISO 17442 LEIs | **21 ms** | ~48 | 9 real GLEIs cycled. ~2 µs per checksum — the mod-97-10 inner loop is not a hot spot today. |
| `split_for_scheme` lazy first-chunk pull (100k rows, Fedwire cap=1) | **1.4 µs** | ~200,000 | Proves laziness — pulling one chunk from a 100k-row input takes microseconds because the generator does not materialise. |
| `split_for_scheme` eager 100k rows (CBPR+ cap=10,000 → 10 chunks) | **26 ms** | 38 | Sustained ~3.8M rows/sec when fully materialised. |
| `generate_xml_string` — 1 row, pacs.008.001.08 | **10.5 ms** | 19 | Dominated by per-call Jinja env setup + XSD parse. |
| `generate_xml_string` — 100 rows | **41 ms** | 22 | Per-row marginal cost amortises ~0.3 ms. |
| `generate_xml_string` — 10,000 rows | **3.3 s** | 0.3 | ~3,000 rows/sec sustained at this size — XSD validation is the long pole. |

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

## Known optimisation opportunities (deliberately deferred)

- **`generate_xml_string` Jinja env reuse.** The current code constructs
  a fresh `jinja2.Environment` and `FileSystemLoader` on every call.
  Caching the env per `(template_dir, msg_type)` would close most of
  the 10.5 ms per-call floor seen on the 1-row test.
- **XSD parse caching.** `xmlschema.XMLSchema(xsd_path)` is reparsed
  on every call. A module-level LRU cache keyed on xsd path would
  remove the longest tail item for batched generation.
- **Streaming-writer XSD validation.** The stream writer currently
  emits valid XML but defers XSD validation to a post-write pass.
  Implementing `iterparse`-based streaming validation against the
  schema would let us validate million-row outputs without buffering.
- **`anyascii` lazy import.** A small win — the import adds ~150 KB
  resident at import-time even for callers that never hit the
  non-Latin fallback path.

These are **explicitly out of scope for the v0.0.2 baseline commit**.
Each warrants its own PR with before/after numbers from this same
benchmark suite as the gate.
