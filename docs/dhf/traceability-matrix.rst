.. _dhf-traceability-matrix:

============================================
Traceability Matrix
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-007
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clause
     - 7.3.10 (Design and Development Files)

1. Forward Traceability: Requirement to Implementation to Test
--------------------------------------------------------------

1.1 FR-100: XML Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-101
     - ``xml/generate_xml.py``
     - ``generate_xml_string()``, ``generate_xml()``
     - ``test_generate_xml.py``, ``test_gold_master.py``
   * - FR-102
     - ``xml/generate_xml.py``
     - ``xml_data_preparers`` dispatch dict
     - ``test_generate_xml.py``, ``test_version_matrix.py``
   * - FR-103
     - ``xml/validate_via_xsd.py``
     - ``validate_xml_string_via_xsd()``, ``validate_via_xsd()``
     - ``test_xsd_validation.py``, ``test_enterprise_xsd.py``,
       ``test_gold_master.py``
   * - FR-104
     - ``xml/register_namespaces.py``
     - ``register_namespaces()``
     - ``test_generate_xml.py``
   * - FR-105
     - ``xml/generate_updated_xml_file_path.py``
     - ``generate_updated_xml_file_path()``
     - ``test_write_xml.py``

1.2 FR-200: Data Ingestion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-201
     - ``csv/load_csv_data.py``
     - ``load_csv_data()``
     - ``test_csv_loader.py``, ``test_csv_validate.py``
   * - FR-202
     - ``json/load_json_data.py``
     - ``load_json_data()``
     - ``test_json_loader.py``
   * - FR-203
     - ``json/load_json_data.py``
     - ``load_jsonl_data()``
     - ``test_json_loader.py``
   * - FR-204
     - ``db/load_db_data.py``
     - ``load_db_data()``
     - ``test_db_loader.py``
   * - FR-205
     - ``parquet/load_parquet_data.py``
     - ``load_parquet_data()``
     - ``test_parquet_loader.py``
   * - FR-206
     - ``core/core.py``
     - ``_determine_data_source_type()`` (dict path)
     - ``test_core_process.py``, ``test_data_loader.py``
   * - FR-207
     - ``core/core.py``
     - ``_determine_data_source_type()`` (list path)
     - ``test_core_process.py``, ``test_data_loader.py``
   * - FR-208
     - ``csv/load_csv_data.py``, ``json/load_json_data.py``,
       ``db/load_db_data_streaming.py``, ``parquet/load_parquet_data.py``
     - ``load_csv_data_streaming()``, ``load_json_data_streaming()``,
       ``load_jsonl_data_streaming()``, ``load_db_data_streaming()``,
       ``load_parquet_data_streaming()``
     - ``test_csv_loader.py``, ``test_json_loader.py``,
       ``test_db_loader.py``, ``test_parquet_loader.py``,
       ``test_data_loader_extended.py``

1.3 FR-300: Validation
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-301
     - ``validation/schema_validator.py``
     - ``SchemaValidator``
     - ``test_validation.py``
   * - FR-302
     - ``validation/bic_validator.py``
     - ``validate_bic()``, ``validate_bic_format()``,
       ``validate_bic_safe()``
     - ``test_bic_validator.py``
   * - FR-303
     - ``validation/iban_validator.py``
     - ``validate_iban()``, ``validate_iban_format()``,
       ``validate_iban_checksum()``, ``validate_iban_safe()``
     - ``test_iban_validator.py``
   * - FR-304
     - ``validation/service.py``, ``csv/validate_csv_data.py``
     - ``ValidationService``, ``validate_csv_data()``
     - ``test_validation_service.py``, ``test_csv_validate.py``
   * - FR-305
     - ``validation/service.py``
     - ``ValidationService``, ``ValidationConfig``,
       ``ValidationReport``, ``ValidationResult``
     - ``test_validation_service.py``

1.4 FR-400: SWIFT Compliance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-401
     - ``compliance/swift_charset.py``
     - Charset validation functions
     - ``test_compliance.py``
   * - FR-402
     - ``compliance/swift_charset.py``
     - Field length enforcement functions
     - ``test_compliance.py``
   * - FR-403
     - ``compliance/swift_charset.py``
     - Transliteration functions
     - ``test_compliance.py``
   * - FR-404
     - ``compliance/swift_charset.py``
     - Compliance report generation
     - ``test_compliance.py``

1.5 FR-500: Version-Specific Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-501
     - ``xml/generate_xml.py``
     - ``_prepare_xml_data_v01()`` (BIC),
       ``_prepare_xml_data_v02_to_v04()`` (BICFI transition)
     - ``test_generate_xml.py``, ``test_version_matrix.py``
   * - FR-502
     - ``xml/generate_xml.py``
     - ``_prepare_xml_data_v08_to_v09()``
     - ``test_generate_xml.py``, ``test_version_matrix.py``
   * - FR-503
     - ``xml/generate_xml.py``
     - ``_prepare_xml_data_v10_to_v12()``
     - ``test_generate_xml.py``, ``test_version_matrix.py``
   * - FR-504
     - ``xml/generate_xml.py``
     - ``_prepare_xml_data_v13()``
     - ``test_generate_xml.py``, ``test_version_matrix.py``
   * - FR-505
     - ``xml/generate_xml.py``
     - ``_prepare_xml_data_v07()``
     - ``test_generate_xml.py``, ``test_version_matrix.py``

1.6 FR-600: Interfaces
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-601
     - ``core/core.py``, ``__init__.py``
     - ``process_files()``, ``generate_xml_string()``
     - ``test_core_process.py``, ``test_main_entry.py``
   * - FR-602
     - ``cli/cli.py``
     - Click command group with options
     - ``test_cli_full.py``, ``test_cli_integration.py``
   * - FR-603
     - ``api/app.py``
     - FastAPI endpoints
     - ``test_api.py``, ``test_api_extended.py``, ``test_api_full.py``
   * - FR-604
     - ``api/job_manager.py``, ``api/app.py``
     - ``create_job()``, ``update_status()``, async endpoints
     - ``test_job_manager.py``, ``test_api_extended.py``,
       ``test_api_full.py``

1.7 FR-700: Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-701
     - ``exceptions.py``
     - ``PaymentValidationError``, ``InvalidIBANError``,
       ``InvalidBICError``, ``MissingRequiredFieldError``
     - ``test_exceptions.py``, ``test_bic_validator.py``,
       ``test_iban_validator.py``
   * - FR-702
     - ``exceptions.py``
     - ``XMLGenerationError``
     - ``test_exceptions.py``, ``test_generate_xml.py``
   * - FR-703
     - ``exceptions.py``
     - ``DataSourceError``
     - ``test_exceptions.py``, ``test_data_loader.py``
   * - FR-704
     - ``exceptions.py``
     - ``ConfigurationError``
     - ``test_exceptions.py``, ``test_constants.py``

1.8 NFR-100: Security
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-101
     - ``xml/validate_via_xsd.py``
     - ``defusedxml.ElementTree.parse()``
     - ``test_xsd_validation.py``
   * - NFR-102
     - ``security/path_validator.py``
     - ``validate_path()``, ``_resolve_within_allowed_bases()``,
       ``_is_allowed_directory()``
     - ``test_path_validator.py``
   * - NFR-103
     - ``security/path_validator.py``, ``logging_schema.py``
     - ``sanitize_for_log()``, PII redaction
     - ``test_path_validator.py``, ``test_logging_schema.py``
   * - NFR-104
     - ``xml/generate_xml.py``
     - ``Environment(autoescape=True)``
     - ``test_generate_xml.py``
   * - NFR-105
     - ``Dockerfile``
     - ``USER appuser``
     - Dockerfile inspection (non-root user)

1.9 NFR-200: Quality
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-201
     - All test files
     - ``--cov-fail-under=99``
     - CI test job (pytest-cov)
   * - NFR-202
     - All source files
     - ``mypy --strict``
     - CI lint job
   * - NFR-203
     - All source files
     - ``bandit -r pacs008/``
     - CI security job
   * - NFR-204
     - All source files
     - ``ruff check``, ``black --check``
     - CI lint job

1.10 NFR-300: Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-301
     - ``pyproject.toml``
     - ``python = "^3.9.2"``
     - CI test matrix (3.9, 3.10, 3.11, 3.12)
   * - NFR-302
     - ``.github/workflows/ci.yml``
     - OS matrix: ubuntu, macos, windows
     - CI test job (3 OS configurations)
   * - NFR-303
     - ``pyproject.toml``
     - Poetry build configuration
     - CI smoke job (install verification)

1.11 NFR-400: Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-401
     - ``xml/validate_via_xsd.py``
     - ``_get_cached_schema()`` (LRU cache, maxsize=16)
     - ``test_xsd_validation.py``, ``test_enterprise_xsd.py``
   * - NFR-402
     - ``csv/load_csv_data.py``, ``json/load_json_data.py``,
       ``db/load_db_data_streaming.py``, ``parquet/load_parquet_data.py``
     - Streaming functions with ``chunk_size`` parameter
     - ``test_csv_loader.py``, ``test_json_loader.py``,
       ``test_db_loader.py``, ``test_parquet_loader.py``
   * - NFR-403
     - ``logging_schema.py``, ``core/core.py``
     - Timing logged via ``log_process_success()``
     - ``test_logging_schema.py``

1.12 NFR-500: Maintainability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-501
     - ``logging_schema.py``
     - ``Events``, ``Fields``, ``log_event()``
     - ``test_logging_schema.py``
   * - NFR-502
     - ``exceptions.py``
     - ``Pacs008Error`` base class hierarchy
     - ``test_exceptions.py``
   * - NFR-503
     - ``xml/generate_xml.py``, ``constants.py``
     - ``xml_data_preparers`` dict, ``valid_xml_types`` list
     - ``test_generate_xml.py``, ``test_constants.py``,
       ``test_version_matrix.py``

2. Reverse Traceability: Test File to Requirements
---------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Test File
     - Requirements Covered
   * - ``test_api.py``
     - FR-603
   * - ``test_api_extended.py``
     - FR-603, FR-604
   * - ``test_api_full.py``
     - FR-603, FR-604
   * - ``test_api_models.py``
     - FR-603
   * - ``test_bic_validator.py``
     - FR-302, FR-701
   * - ``test_cli_full.py``
     - FR-602
   * - ``test_cli_integration.py``
     - FR-602
   * - ``test_compliance.py``
     - FR-401, FR-402, FR-403, FR-404
   * - ``test_constants.py``
     - FR-102, FR-704, NFR-503
   * - ``test_context.py``
     - NFR-501
   * - ``test_core_process.py``
     - FR-101, FR-206, FR-207, FR-601
   * - ``test_coverage_gaps.py``
     - NFR-201
   * - ``test_csv_loader.py``
     - FR-201, FR-208
   * - ``test_csv_validate.py``
     - FR-201, FR-304
   * - ``test_data_loader.py``
     - FR-201, FR-202, FR-203, FR-204, FR-205, FR-206, FR-207
   * - ``test_data_loader_extended.py``
     - FR-201, FR-202, FR-203, FR-204, FR-205, FR-208
   * - ``test_db_loader.py``
     - FR-204, FR-208, NFR-102
   * - ``test_enterprise_xsd.py``
     - FR-103, NFR-401
   * - ``test_exceptions.py``
     - FR-701, FR-702, FR-703, FR-704, NFR-502
   * - ``test_final_coverage.py``
     - NFR-201
   * - ``test_generate_xml.py``
     - FR-101, FR-102, FR-104, FR-501, FR-502, FR-503, FR-504, FR-505,
       FR-702, NFR-104
   * - ``test_gold_master.py``
     - FR-101, FR-102, FR-103
   * - ``test_iban_validator.py``
     - FR-303, FR-701
   * - ``test_job_manager.py``
     - FR-604
   * - ``test_json_loader.py``
     - FR-202, FR-203, FR-208
   * - ``test_logging_schema.py``
     - NFR-103, NFR-403, NFR-501
   * - ``test_main_entry.py``
     - FR-601
   * - ``test_parquet_loader.py``
     - FR-205, FR-208
   * - ``test_path_validator.py``
     - NFR-102, NFR-103
   * - ``test_remaining_gaps.py``
     - NFR-201
   * - ``test_validation.py``
     - FR-301, FR-304
   * - ``test_validation_service.py``
     - FR-305
   * - ``test_version_matrix.py``
     - FR-102, FR-501, FR-502, FR-503, FR-504, FR-505, NFR-503
   * - ``test_write_xml.py``
     - FR-105
   * - ``test_xsd_validation.py``
     - FR-103, NFR-101, NFR-401

3. Risk Control Traceability
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Risk ID
     - Mitigation
     - Source Module
     - Verification Test(s)
   * - R-001
     - XSD validation of all generated XML
     - ``xml/validate_via_xsd.py``
     - ``test_xsd_validation.py``, ``test_gold_master.py``
   * - R-002
     - defusedxml for all XML parsing
     - ``xml/validate_via_xsd.py``
     - ``test_xsd_validation.py``
   * - R-003
     - Path validation with directory jail
     - ``security/path_validator.py``
     - ``test_path_validator.py``
   * - R-004
     - SQL input validation
     - ``db/load_db_data.py``
     - ``test_db_loader.py``
   * - R-005
     - BIC + IBAN validators
     - ``validation/bic_validator.py``,
       ``validation/iban_validator.py``
     - ``test_bic_validator.py``, ``test_iban_validator.py``
   * - R-006
     - SWIFT charset validation
     - ``compliance/swift_charset.py``
     - ``test_compliance.py``
   * - R-007
     - SWIFT field length enforcement
     - ``compliance/swift_charset.py``
     - ``test_compliance.py``
   * - R-008
     - Version string allowlist
     - ``constants.py``
     - ``test_constants.py``, ``test_version_matrix.py``
   * - R-009
     - Log sanitization
     - ``security/path_validator.py``,
       ``logging_schema.py``
     - ``test_path_validator.py``, ``test_logging_schema.py``
   * - R-010
     - Dependency pinning + safety scanner
     - ``pyproject.toml``, CI ``security`` job
     - CI pipeline verification
   * - R-011
     - Gold master tests for all 13 versions
     - ``templates/pacs.008.001.XX/``
     - ``test_gold_master.py``, ``test_version_matrix.py``
   * - R-012
     - Jinja2 autoescape=True
     - ``xml/generate_xml.py``
     - ``test_generate_xml.py``
