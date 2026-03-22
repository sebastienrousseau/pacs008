.. _dhf-design-development-plan:

======================================
Design and Development Plan
======================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-002
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.1 (Design and Development Planning), 7.3.2 (Design and Development Inputs)

1. Scope
--------

The **pacs008** library generates ISO 20022 pacs.008 FI-to-FI Customer Credit
Transfer XML messages. It ingests payment data from multiple sources (CSV, JSON,
JSONL, SQLite, Parquet, Python objects), generates standards-compliant XML, and
validates output against official XSD schemas.

The library supports all 13 published versions of the pacs.008 message type
(pacs.008.001.01 through pacs.008.001.13).

2. Applicable Standards
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Standard
     - Application
   * - ISO 20022
     - Financial message schema (pacs.008 message type)
   * - ISO 15022
     - SWIFT message standard (predecessor, charset reference)
   * - ISO 9362
     - BIC (Business Identifier Code) format and validation
   * - ISO 7064
     - IBAN check-digit algorithm (mod-97-10)
   * - ISO 4217
     - Currency code set
   * - ISO 13485:2016
     - Quality management system (DHF structure)
   * - ISO 14971:2019
     - Risk management (applied to software risks)
   * - IEC 62304:2006+A1
     - Medical device software lifecycle (process framework)

3. Development Methodology
--------------------------

The project follows an **iterative, test-driven, CI-gated** methodology:

- **Test-Driven Development (TDD):** Tests are written alongside or before
  implementation. No code merges without passing tests.
- **Continuous Integration:** Every commit triggers automated lint, type-check,
  security scan, and full test suite execution.
- **Quality Gates:** All gates must pass before any change is accepted into the
  main branch.
- **Signed Commits:** All commits are cryptographically signed for traceability.

4. Development Phases
---------------------

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Phase
     - Name
     - Deliverables
   * - 1
     - Core XML Generation
     - Jinja2 template engine, version dispatch, XSD validation, namespace
       registration, ``generate_xml_string()`` API
   * - 2
     - Multi-Format Data Ingestion
     - CSV, JSON, JSONL, SQLite, Parquet loaders with streaming support,
       universal ``load_payment_data()`` dispatcher
   * - 3
     - Validation Framework
     - BIC validator (ISO 9362), IBAN validator (ISO 7064 mod-97-10), JSON
       schema validation for all 13 versions, ``ValidationService`` with
       configurable rules
   * - 4
     - SWIFT Compliance
     - Charset validation (Z/z character set), field length enforcement,
       transliteration, compliance report generation
   * - 5
     - Interface Layer
     - Python public API (``process_files()``, ``generate_xml_string()``),
       Click CLI with ``--dry-run`` and ``--verbose``, FastAPI REST API with
       async job management
   * - 6
     - Security Hardening
     - defusedxml for XXE prevention, path traversal jail, SQL input
       validation, log sanitization, Jinja2 autoescape
   * - 7
     - Verification & Release
     - 1,417 tests, 100% branch coverage, gold master fixtures for all 13
       versions, Bandit SAST scan, cross-platform CI (3 OS x 4 Python versions)

5. Tools and Environment
------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Category
     - Tool
     - Purpose
   * - Language
     - Python 3.9+
     - Runtime (3.9, 3.10, 3.11, 3.12 supported)
   * - Package Manager
     - Poetry
     - Dependency management and build
   * - Testing
     - pytest
     - Test runner with markers, fixtures, parametrize
   * - Coverage
     - pytest-cov
     - Branch coverage reporting (99% minimum gate)
   * - Type Checking
     - mypy (strict)
     - Static type analysis, ``disallow_untyped_defs=true``
   * - Linting
     - ruff, black
     - Code style enforcement (line-length=79)
   * - Security
     - Bandit
     - Static application security testing (SAST)
   * - CI
     - GitHub Actions
     - Automated pipeline (test, lint, security, smoke)
   * - Documentation
     - Sphinx + RTD theme
     - ReStructuredText documentation
   * - Containers
     - Docker
     - ``python:3.12-slim`` with non-root user
   * - Pre-commit
     - pre-commit
     - 13 hooks (trailing whitespace, YAML/JSON/TOML check, ruff, black, mypy,
       detect-private-key, etc.)

6. Quality Gates
----------------

Every commit must pass all of the following before merge:

1. **Lint & Format:** ``ruff check`` and ``black --check`` pass with zero findings
2. **Type Check:** ``mypy --strict`` passes with zero errors
3. **Security Scan:** ``bandit -r pacs008/`` reports zero issues
4. **Unit Tests:** All 1,417 tests pass
5. **Branch Coverage:** >= 99% (enforced via ``--cov-fail-under=99``)
6. **Smoke Tests:** Quick sanity checks pass
7. **Pre-commit Hooks:** All 13 hooks pass

7. Deliverables
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Deliverable
     - Description
   * - Source Code
     - ``pacs008/`` package with 14 sub-packages, 43 Python modules
   * - Test Suite
     - ``tests/`` directory with 36 test files, 1,417 test cases
   * - Documentation
     - Sphinx docs including this DHF document set
   * - CI Pipeline
     - ``.github/workflows/ci.yml`` with 4 workflow jobs
   * - Docker Image
     - ``Dockerfile`` for containerized deployment
   * - PyPI Package
     - Distributable package via ``poetry build``
   * - Templates
     - 13 Jinja2 templates + 13 XSD schemas + 13 sample XML files
