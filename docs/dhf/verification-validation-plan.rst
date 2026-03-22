.. _dhf-verification-validation:

============================================
Verification and Validation Plan
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-006
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.5 (Verification), 7.3.6 (Validation), 7.3.7 (Design Transfer)

1. Test Strategy
----------------

The verification strategy follows a layered approach from unit tests through
system-level validation:

1. **Unit Tests** — Individual functions and classes tested in isolation
2. **Integration Tests** — Module interactions and data flow pipelines
3. **System Tests** — End-to-end workflows from data ingestion through XML
   output and validation
4. **Regression Tests** — Gold master comparison against known-good reference
   outputs for all 13 versions

All tests are automated and executed on every commit via GitHub Actions CI.

2. Test Categories and Markers
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Marker
     - Category
     - Description
   * - ``smoke``
     - Smoke
     - Quick sanity checks confirming core functionality is operational.
       Run first in CI for fast feedback.
   * - ``integration``
     - Integration
     - End-to-end workflow tests spanning multiple modules. Verify that
       components work together correctly.
   * - ``security``
     - Security
     - XXE prevention, path traversal, injection attack, and log
       sanitization tests.
   * - ``version_compat``
     - Version Compatibility
     - Tests exercising all 13 pacs.008 versions (v01 through v13).
       Verify version dispatch and version-specific features.
   * - ``perf``
     - Performance
     - Benchmark tests measuring generation throughput and resource usage.
   * - ``slow``
     - Slow
     - Tests taking more than 1 second. May be excluded from rapid
       development cycles.

**Running specific categories:**

.. code-block:: bash

   pytest -m smoke              # Quick sanity checks
   pytest -m integration        # End-to-end workflows
   pytest -m security           # Security-focused tests
   pytest -m version_compat     # All 13 versions
   pytest -m perf               # Performance benchmarks

3. Test File Inventory
-----------------------

3.1 Core Processing Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_core_process.py``
     - ``process_files()`` orchestration with all data source types
     - FR-101, FR-601
   * - ``test_main_entry.py``
     - ``__main__.py`` entry point and ``main()`` function
     - FR-601
   * - ``test_constants.py``
     - ``valid_xml_types`` list, ``BASE_DIR``, ``SCHEMAS_DIR``,
       ``TEMPLATES_DIR``
     - FR-102, NFR-503
   * - ``test_context.py``
     - Application context singleton
     - NFR-501
   * - ``test_exceptions.py``
     - Exception hierarchy and custom exception fields
     - FR-701, FR-702, FR-703, FR-704

3.2 XML Generation and Validation Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_generate_xml.py``
     - XML generation for all 13 versions, version dispatch mechanism
     - FR-101, FR-102, FR-104, FR-501–FR-505
   * - ``test_xsd_validation.py``
     - ``validate_via_xsd()``, ``validate_xml_string_via_xsd()``, XXE
       prevention
     - FR-103, NFR-101
   * - ``test_enterprise_xsd.py``
     - XSD validation at enterprise scale
     - FR-103, NFR-401
   * - ``test_write_xml.py``
     - ``write_xml_to_file()`` output
     - FR-105
   * - ``test_gold_master.py``
     - End-to-end gold master: source → ingestion → XML → XSD for all
       13 versions
     - FR-101, FR-102, FR-103
   * - ``test_version_matrix.py``
     - Version compatibility matrix across all 13 versions
     - FR-102, FR-501–FR-505

3.3 Data Ingestion Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_csv_loader.py``
     - ``load_csv_data()``, ``load_csv_data_streaming()``
     - FR-201, FR-208
   * - ``test_csv_validate.py``
     - ``validate_csv_data()`` input validation
     - FR-201, FR-304
   * - ``test_json_loader.py``
     - ``load_json_data()``, ``load_jsonl_data()``, streaming variants
     - FR-202, FR-203, FR-208
   * - ``test_db_loader.py``
     - ``load_db_data()``, ``load_db_data_streaming()``, SQL input
       validation
     - FR-204, FR-208, NFR-102
   * - ``test_parquet_loader.py``
     - ``load_parquet_data()``, ``load_parquet_data_streaming()``
     - FR-205, FR-208
   * - ``test_data_loader.py``
     - Universal ``load_payment_data()`` dispatch mechanism
     - FR-201–FR-207
   * - ``test_data_loader_extended.py``
     - Extended data loader tests with multiple formats
     - FR-201–FR-208

3.4 Validation Tests
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_bic_validator.py``
     - BIC format validation (ISO 9362), country code validation
     - FR-302
   * - ``test_iban_validator.py``
     - IBAN format + ISO 7064 mod-97-10 checksum verification
     - FR-303
   * - ``test_validation.py``
     - Validation module integration
     - FR-301, FR-304
   * - ``test_validation_service.py``
     - ``ValidationService``, ``ValidationConfig``, ``ValidationReport``,
       ``ValidationResult``
     - FR-305

3.5 Compliance Tests
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_compliance.py``
     - SWIFT charset validation, field length enforcement, transliteration
     - FR-401, FR-402, FR-403, FR-404

3.6 Interface Tests
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_api.py``
     - Basic FastAPI endpoints: ``/api/health``, ``/api/validate``,
       ``/api/generate``
     - FR-603
   * - ``test_api_extended.py``
     - Extended API functionality and edge cases
     - FR-603, FR-604
   * - ``test_api_full.py``
     - Comprehensive API integration tests
     - FR-603, FR-604
   * - ``test_api_models.py``
     - Pydantic request/response models (``MessageType``,
       ``DataSourceType`` enums)
     - FR-603
   * - ``test_cli_full.py``
     - Full CLI workflow with all options
     - FR-602
   * - ``test_cli_integration.py``
     - CLI integration with real file processing
     - FR-602
   * - ``test_job_manager.py``
     - Async job management: ``JobStatus``, ``create_job()``,
       ``update_status()``
     - FR-604

3.7 Security Tests
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_path_validator.py``
     - Path traversal protection: ``validate_path()``,
       ``PathValidationError``, ``SecurityError``, ``sanitize_for_log()``
     - NFR-102, NFR-103
   * - ``test_logging_schema.py``
     - Structured logging: ``Events``, ``Fields``, ``log_event()``, PII
       redaction
     - NFR-103, NFR-501

3.8 Coverage Gap Tests
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_coverage_gaps.py``
     - Additional coverage for uncovered code paths
     - NFR-201
   * - ``test_final_coverage.py``
     - Final coverage gaps (mutation testing)
     - NFR-201
   * - ``test_remaining_gaps.py``
     - Remaining code coverage gaps
     - NFR-201

4. Gold Master Tests
--------------------

The ``test_gold_master.py`` file provides end-to-end regression testing for all
13 pacs.008 versions. For each version:

1. Load reference payment data from a known input fixture
2. Generate XML using the version-specific template and preparer
3. Validate generated XML against the official XSD schema
4. Compare output against a known-good reference XML file

**Gold master fixtures** are stored in ``pacs008/templates/pacs.008.001.XX/``
as ``.xml`` reference files for each of the 13 versions.

5. Static Analysis Tools
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Tool
     - Type
     - Configuration
   * - mypy
     - Type checking
     - ``python_version=3.9``, ``strict=true``,
       ``disallow_untyped_defs=true``
   * - ruff
     - Linting
     - ``line-length=79``, ``target-version=py39``
   * - black
     - Formatting
     - ``line-length=79``, ``target-version=['py39']``
   * - bandit
     - SAST
     - ``bandit -r pacs008/`` — zero findings required
   * - safety
     - Dependency audit
     - Checks pinned dependencies against known vulnerability database

6. CI Pipeline
--------------

The GitHub Actions CI pipeline (``.github/workflows/ci.yml``) runs on every
push and pull request:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Job
     - Matrix
     - Actions
   * - **test**
     - 3 OS (ubuntu, macos, windows) x 4 Python (3.9, 3.10, 3.11, 3.12)
     - Install dependencies, run full test suite with coverage, upload
       coverage to Codecov (Python 3.12 / ubuntu only)
   * - **smoke**
     - ubuntu-latest, Python 3.12
     - Run ``pytest -m smoke`` for quick sanity checks, verify example
       scripts
   * - **lint**
     - ubuntu-latest, Python 3.12
     - Run ``ruff check``, ``black --check``, ``mypy --strict``
   * - **security**
     - ubuntu-latest, Python 3.12
     - Run ``bandit -r pacs008/`` for SAST scan

**Total CI matrix:** 14 configurations (12 test + 1 lint + 1 security)

7. Acceptance Criteria
-----------------------

The software release is accepted when **all** of the following are satisfied:

.. list-table::
   :header-rows: 1
   :widths: 10 60 30

   * - #
     - Criterion
     - Verification Method
   * - 1
     - All 1,417 tests pass on all CI matrix configurations
     - GitHub Actions test job (12 configs)
   * - 2
     - Branch coverage >= 99% (actual: 100%)
     - ``--cov-fail-under=99`` in pytest
   * - 3
     - Zero bandit SAST findings
     - GitHub Actions security job
   * - 4
     - Zero mypy strict-mode errors
     - GitHub Actions lint job
   * - 5
     - Zero ruff/black formatting violations
     - GitHub Actions lint job
   * - 6
     - All 13 gold master tests pass (one per pacs.008 version)
     - ``test_gold_master.py``
   * - 7
     - All pre-commit hooks pass
     - ``.pre-commit-config.yaml`` (13 hooks)
   * - 8
     - All XSD schemas validate correctly
     - ``test_xsd_validation.py``, ``test_enterprise_xsd.py``
   * - 9
     - All risk mitigations verified by tests
     - DHF-005 Risk Control Verification table
