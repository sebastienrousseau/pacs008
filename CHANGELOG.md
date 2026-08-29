# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.11] - 2026-08-29

Suite alignment release. Every package in the `pacs008` suite now ships the
same number: `pacs008`, `pacs008-mcp` and `pacs008-loader-mt103` were at
0.0.10, 0.0.9 and 0.0.3 respectively — three numbers for one suite, and no
way for a user to reason about which combination was intended.

### Fixed

- **`constants.VERSION` said `0.0.1`.** It had said so since the first
  release, through nine subsequent ones, so anything reading it reported a
  version that had not been current for months.

  It survived because the test guarding it asserted `VERSION == "0.0.1"`.
  A pinned literal does not guard a value; it preserves whatever it was
  set to. The test now compares against `pacs008.__version__`, and the
  shared conformance file checks every restatement of the version agrees.

### Added

- **`benches/bench_batch_pipeline.py`** — what a batch costs to cleanse
  and split.

  **Cleansing is linear** (`us/row` moves 1.19x between 100 and 50,000
  rows) and dominates, at ~10 µs per row. **Splitting is arithmetic**, at
  about 3% of cleansing. `validate_swift_charset` is ~0.5 µs per value and
  is the innermost loop — per character, per field, per row — so a change
  there multiplies through everything above it.

  Recorded because it is easy to get wrong: `split_for_scheme` returns a
  **generator**. Timing the bare call measures building the generator
  object, reports that splitting is free, and measures nothing. It is
  benchmarked consumed.

- **`scripts/check_suite_consistency.py`** and a scheduled
  **`suite-consistency`** workflow, modelled on `camt053`'s. It compares
  every published member against the core and fails when they disagree —
  and catches the version bumped in the tree but never released, which has
  happened three times elsewhere in this suite and each time stranded a
  security floor that reached nobody.

- **`tests/test_suite_conformance.py`** — invariants shared across the
  suite, vendored from one canonical copy and checksummed by its own test.

### Changed

- CI lints and formats `benches/` and `scripts/`, and runs the benchmark.

## [0.0.10] - 2026-08-28

Swift deferred the CBPR+ structured-address start date; the library still
described it as in force.

### Fixed

- The CBPR+ profile and `standards/address` said the structured-address
  requirement takes force on 14 November 2026. Swift accepted a community
  request on 27 August 2026 and deferred every payments change in Standards
  Release 2026, confirming replacement timing by December at the latest. The
  requirement itself was agreed by the community in 2023 and stands; only
  when it bites has moved.
- `standards/address` said the date bound "all major schemes". The deferral
  is Swift's and covers CBPR+ only. HVPS+, T2 RTGS, CHAPS, Lynx and Fedwire
  set their own dates and are unchanged; each now says whose date it is.

### Unchanged

- Every rule, threshold and validation result. `NOV_2026_CLIFF` keeps its
  value deliberately: five profiles switch address policy on it, and with no
  CBPR+ date to switch on, the literal reading is that unstructured
  addresses stay acceptable indefinitely — true of the rulebook and useless
  as advice. Swift asked the community to keep pressing ahead.

## [0.0.9] - 2026-08-16

Release the `cryptography` ceiling that was raised in the tree but never
published.

### Fixed

- `cryptography` is now `>=46.0.7,<51.0.0`. The published `0.0.8` still
  carried `<50.0.0`, which made `cryptography 50.0.0` — the version that
  patches the high-severity advisory — unresolvable for every dependent.
  `pacs008-mcp` could not install at all:

      ERROR: Cannot install cryptography>=50.0.0, pacs008==0.0.7 and
      pacs008==0.0.8 because these package versions have conflicting
      dependencies.

### Added

- `tests/test_package_version.py`, pinning `__version__` to
  `pyproject.toml`, `SECURITY.md` and the newest `CHANGELOG.md` heading,
  and checking the changelog is ordered newest-first. Nothing previously
  tied these together, so a release could ship with them disagreeing —
  which is how `0.0.8` came to be published with a constraint the tree
  had already changed.

## [0.0.8] - 2026-07-26

Ship the library's internal type information to consumers. `pacs008` has
been `mypy --strict` clean for some time, but shipped no PEP 561 marker, so
downstream projects received **none** of those annotations under `mypy` or
`pyright`.

### Added

- **PEP 561 `py.typed` marker** (`pacs008/py.typed`), wired into the Poetry
  `include` list and verified present in the built wheel. Downstream code
  now type-checks against `pacs008`'s real annotations.
- **Regression tests** (`tests/test_py_typed_marker.py`) that fail before a
  release ships if the marker is dropped from the source tree or the
  packaging includes.

### Changed

- Version `0.0.7` → `0.0.8`; `SECURITY.md` supported-versions table
  reconciled to `0.0.8`.

## [0.0.7] - 2026-07-18

The **numeric-string validation** fix. Closes issue #6: JSON payloads whose
`nb_of_txs` and `interbank_settlement_amount` fields arrive as numeric
*strings* — the representation CSV-origin rows and many JSON producers emit —
were rejected by the JSON-schema layer behind `/api/validate` and
`/api/generate`, even though the row loader (`validate_csv_data`) accepted
them. The two validators now agree.

### Fixed

- **JSON schemas** (`pacs008/schemas/*.schema.json`): `nb_of_txs` now accepts
  an integer **or** a numeric string (ISO 20022 `Max15NumericText`), and
  `interbank_settlement_amount` accepts a number **or** a decimal string
  (ISO 20022 decimal amount). A `pattern` guards each string branch so
  genuinely invalid input (non-numeric text, negative or zero counts,
  non-integral counts, malformed decimals) is still rejected. Applied to all
  18 schemas carrying `nb_of_txs` and all 16 carrying
  `interbank_settlement_amount`. (#6)

### Added

- Regression tests (`tests/test_validation.py::TestIssue6NumericStringFields`)
  covering the reporter's native-scalar payload, the numeric-string form
  across every pacs.008 version (v01–v13), the combined loader + schema
  surface, and invalid-input rejection.

## [0.0.6] - 2026-07-16

The **suite alignment** cut. pacs008 0.0.5 was the last member of the
ISO 20022 MCP suite capping `rich<14` and `markupsafe<3`, forcing every
co-installation (`iso20022-mcp[all]`) to float on old versions. This
release raises the caps to match the published constraints of
camt053 0.0.14 and acmt001 0.0.3. No API changes.

### Changed

- **rich** `^13.7` (`>=13.7,<14`) → `>=13.7.1,<16`, matching
  camt053/acmt001. Co-installs are now bound by pain001's `rich<15`
  instead of pacs008.
- **markupsafe** `^2.1` (`>=2.1,<3`) → `>=2.1,<4`, matching
  camt053/acmt001; co-installs resolve markupsafe 3.x.
- **cryptography** `<49.0.0` → `<50.0.0`, matching the
  `>=48.0.1,<50.0.0` constraint published by camt053/acmt001
  (cross-suite cap audit).
- **pyarrow** `<24.0.0` → `<26.0.0`, matching acmt001's `<26.0.0`
  (cross-suite cap audit).

The full test suite (1875 tests, 96% branch-coverage gate) passes at
both ends of every widened range: floors
(rich 13.7.1 / markupsafe 2.1.0 / cryptography 46.0.7 / pyarrow 18.0.0)
and ceilings
(rich 15.0.0 / markupsafe 3.0.3 / cryptography 49.0.0 / pyarrow 25.0.0).

## [0.0.5] - 2026-07-12

The **security & robustness** cut. Publishes the dependency and validation
fixes already on `main` so downstream companions (e.g. `pacs008-mcp`) resolve
patched transitive dependencies. No API changes.

### Security

- **cryptography** constraint widened from `<47.0.0` to `<49.0.0`, allowing
  the patched `>=48.0.1` release (vulnerable-OpenSSL-in-wheels advisory).
  Clears the alert inherited by downstream packages pinned to `pacs008`.

### Fixed

- JSON/JSONL payment validation now accepts native scalar types (int, float,
  bool) without raising `AttributeError`; falsy-but-present values (`0`,
  `0.0`, `False`) are no longer treated as missing, and bool-for-int /
  non-integral-float are correctly rejected.

## [0.0.4] - 2026-06-13

### Removed

- **Python 3.9 support dropped.** Python 3.9 reached end-of-life on
  2025-10-04; v0.0.3 already shipped CVE fixes whose upstream
  versions had themselves dropped 3.9 support, leaving 3.9 users in
  a "transitional" tier with known vulnerabilities. v0.0.4 closes
  that gap by raising the floor to Python 3.10. Existing 3.9
  deployments should pin to `pacs008==0.0.3` and plan a 3.10+
  upgrade.

### Changed

- `python = "^3.9.2"` → `python = "^3.10"` in `pyproject.toml`.
- Tooling targets updated in lockstep:
  - `[tool.black] target-version = ['py39']` → `['py310']`
  - `[tool.ruff] target-version = "py39"` → `"py310"`
  - `[tool.mypy] python_version = "3.9"` → `"3.10"`
  - `black` dev dep no longer conditional on `python >= 3.10`.
- CI matrix `python-version` reduced from `[3.9, 3.10, 3.11, 3.12]`
  to `[3.10, 3.11, 3.12]` — 9 matrix entries (3 OS × 3 Python)
  instead of 12.
- Ruff modernised 113 type annotations to py310 idioms
  (`X | Y` over `Optional[X] / Union[X, Y]`, `isinstance(x, X | Y)`
  over `isinstance(x, (X, Y))`, etc.) via `--unsafe-fixes`. Pure
  cosmetic — no behaviour change.

### Security

The 7 Dependabot alerts remaining open after v0.0.3 close
automatically with this release: with Python 3.9 out of scope, the
lockfile no longer needs dual-version entries, so every install
resolves directly to the fixed transitive versions:

  pyarrow 23.0.1, urllib3 2.7.0, starlette 1.3.1,
  python-dotenv 1.2.2, pytest 9.1.0, requests 2.34.2.

[0.0.4]: https://github.com/sebastienrousseau/pacs008/compare/v0.0.3...v0.0.4

## [0.0.3] - 2026-06-13

### Security

Patch release closing 8 Dependabot security advisories flagged after
v0.0.2 shipped. All fixes are applied via lock-file updates;
Python 3.10+ users get the fixed versions automatically, Python 3.9
users keep the latest 3.9-compatible versions (the upstream fixes
all dropped Python 3.9 support, since 3.9 EOL was October 2025).

| Package | py3.9 (transitional) | py3.10+ (fixed) | CVE summary |
|---|---|---|---|
| `pyarrow` | 21.0.0 | **23.0.1** | Use-after-free reading IPC files with pre-buffering (×2 advisory channels, HIGH) |
| `urllib3` | 2.6.3 | **2.7.0** | Decompression-bomb safeguard bypass + sensitive-header forwarding across proxied redirects (HIGH) |
| `starlette` | 0.49.3 | **1.3.1** | Missing Host header validation enables path-based security bypass (MEDIUM) |
| `python-dotenv` | 1.2.1 | **1.2.2** | Symlink-follow in `set_key` allows arbitrary file overwrite (MEDIUM) |
| `pytest` | 8.4.2 | **9.1.0** | Vulnerable `tmpdir` handling (MEDIUM, dev-only) |
| `requests` | 2.32.5 | **2.34.2** | Insecure temp-file reuse in `extract_zipped_paths` (MEDIUM) |

### Changed

- `pyarrow` constraint widened from `>=18.0.0,<22.0.0` to
  `>=18.0.0,<24.0.0` to admit the 23.x fix.
- `pytest` constraint widened from `^8.0.0` to `>=8.0,<10` to admit
  9.1.0 in dev environments.
- No code changes — pure dep bumps.

### Known limitations

Python 3.9 environments still carry the CVEs above because their fix
versions dropped 3.9 support. A 3.9 drop is planned for v0.0.4 /
v0.1.0; until then Python 3.9 users on production-sensitive paths
should upgrade to Python 3.10+ to get the fixed transitive
dependencies.

[0.0.3]: https://github.com/sebastienrousseau/pacs008/compare/v0.0.2...v0.0.3

## [0.0.2] - 2026-06-13

### Added

- **Scheme profiles** — `pacs008.profiles` package with `SchemeProfile` ABC
  and 7 concrete profiles (`generic`, `cbpr_plus`, `fedwire`, `chaps`,
  `hvps_plus`, `t2_rtgs`, `sct_inst`) encoding charge bearers, UETR
  requirements, batch cardinality, version pinning, character set,
  settlement calendar, address policy, and LEI requirements per scheme.
- **Postal-address tooling for the November 14, 2026 cliff** —
  `pacs008.standards.address` with `PostalAddress` (ISO 20022
  `PostalAddress27`), `AddressClassification`, `AddressPolicy`, and
  `from_unstructured` country-aware converters for GB / US / DE / FR / JP.
- **Business Application Header (BAH) wrapping** —
  `pacs008.standards.bah` with `wrap_in_bah` / `extract_bah_fields` for
  `head.001.001.02` envelopes required by CBPR+ / HVPS+.
- **Inbound parser with `MsgDefIdr` dispatch** — `pacs008.xml.parser`
  classifies any pacs / pain / camt / head / admi message
  (envelope-wrapped or bare) into a typed `ParsedMessage`.
- **LEI validator** — `pacs008.validation.lei_validator` implements ISO
  17442 format checks and ISO 7064 mod-97-10 checksum verification.
- **Settlement-date calendars** — `pacs008.validation.calendar` with
  `TARGETCalendar`, `FedwireCalendar`, `CHAPSCalendar`, `AlwaysOpenCalendar`
  (computational rules — Easter via the anonymous Gregorian algorithm,
  Sun→Mon substitution for Fedwire, weekend-bumping substitution for CHAPS).
- **Verification of Payee (VoP)** — `pacs008.vop` with `VoPMatchResult`,
  `VoPResult`, embed/extract helpers, and `validate_vop_results` for the
  EPC mandate in force since 9 October 2025.
- **Idempotency layer** — `pacs008.idempotency` with `IdempotencyStore`
  ABC, in-memory LRU + TTL store, and SQLite-backed persistent store.
  Default policy fails closed on duplicates.
- **Constant-memory streaming XML writer** — `pacs008.xml.stream_writer`
  uses `lxml.etree.xmlfile` for 100k+ row batches without OOMing.
- **Scheme-aware batch splitter** — `pacs008.core.splitter` with
  `required_chunks` and lazy generator `split_for_scheme` for SCT Inst /
  Fedwire one-tx-per-file rails.
- **Signed audit envelope (Ed25519)** — `pacs008.observability.audit`
  produces tamper-evident `AuditRecord` summaries (input hash, output
  hash, validator decisions, scheme, ISO 8601 timestamp, signature) for
  DORA-aligned audit trails.
- **Optional OpenTelemetry tracing** — `pacs008.observability.otel`
  exposes `trace_span` / `add_attribute` with `PACS008_OTEL_ENABLED`
  env-var gating. No-op when the `[otel]` extra is not installed.
- **Non-Latin script transliteration** in `pacs008.compliance.swift_charset`
  via `anyascii` (Cyrillic / CJK / Arabic / Greek / Hebrew / Devanagari)
  replacing the prior dot-only fallback. Added `policy="reject"` mode and
  `SWIFT_Z_CHARSET` (X + Latin-1 supplement for Fedwire-style profiles).
- **`scheme` parameter** added to `pacs008.core.core.process_files` —
  raises `SchemeViolationError` aggregating all findings.
- **Governance**: `SECURITY.md`, `.github/CODEOWNERS`,
  `.github/PULL_REQUEST_TEMPLATE.md`, issue templates
  (`bug.yml`, `feature.yml`, `config.yml`).

### Changed

- **Refactored `pacs008.logging_schema`** (1,070 lines) into the
  `pacs008.observability` package (`events`, `fields`, `tracing`,
  `redaction`, `formatters`, `metrics`). `pacs008.logging_schema` remains
  as a thin re-export shim — existing imports keep working.
- **Runtime dependencies widened** from exact pins to caret ranges so
  downstream applications can resolve `pacs008` alongside their own
  dep tree. `poetry.lock` is now committed for reproducible CI / Docker
  builds.
- **README rewritten** to a centred branding + grouped TOC layout, with
  a self-contained runnable example per capability (~640 lines down
  from 1,262).
- **PyPI description** widened to reflect the broader feature surface
  (scheme profiles, BAH, parser, audit envelope).
- **Coverage gate lowered** from `99` to `90` percent.

### Fixed

- REST API endpoint paths in the README corrected to the `/api/*` prefix
  matching the actual FastAPI routes (was missing the prefix).
- `cardinality_exceeded` violation message now includes the required
  chunk count and points at `pacs008.core.splitter.split_for_scheme` so
  operators get an actionable next step.
- Mypy and ruff clean across the entire new public surface.

### Removed

- `tests/test_coverage_gaps.py`, `tests/test_final_coverage.py`,
  `tests/test_remaining_gaps.py` — three files (2,362 LOC combined) that
  existed only to satisfy the 99% coverage gate.

### Security

- Merged upstream Dependabot security minimums while widening ranges:
  `pygments ^2.20`, `cryptography >=46.0.7,<47.0.0`,
  `black {version = "^26.3.1", python = ">=3.10"}`.

[0.0.2]: https://github.com/sebastienrousseau/pacs008/compare/v0.0.1...v0.0.2

## [0.0.1] - 2026-03-21

### Added

- Initial release of pacs008 library
- Support for all 13 ISO 20022 pacs.008 versions (001.01 through 001.13)
- Multi-source data ingestion: CSV, JSON, JSONL, SQLite, Parquet
- Jinja2-based XML template engine with XSD validation
- SWIFT compliance module: charset validation, field length enforcement,
  transliteration, and silent rejection prevention
- FastAPI REST API with async job management
- Click-based CLI for batch processing
- BIC and IBAN validators
- JSON schema validation for all 13 versions
- Path traversal protection and security hardening
- 1,400+ tests with 100% code coverage
- Gold master E2E test fixtures for all 13 versions
- Cross-platform CI (macOS + Linux, Python 3.9-3.12)

[0.0.1]: https://github.com/sebastienrousseau/pacs008/releases/tag/v0.0.1
