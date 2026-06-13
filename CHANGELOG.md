# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
