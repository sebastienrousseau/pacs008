# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
