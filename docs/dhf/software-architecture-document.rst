.. _dhf-software-architecture:

============================================
Software Architecture Document
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-004
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clause
     - 7.3.4 (Design and Development Review)

1. Module Architecture
----------------------

The pacs008 library is organized into 14 packages, each with a single
responsibility:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Package
     - Responsibility
   * - ``api/``
     - FastAPI REST API application (``app.py``), async job management
       (``job_manager.py``), Pydantic request/response models (``models.py``)
   * - ``cli/``
     - Click-based command-line interface (``cli.py``) with options for message
       type, template, schema, data, output directory, dry-run, and verbose
   * - ``compliance/``
     - SWIFT compliance: charset validation (Z/z set), field length
       enforcement, transliteration (``swift_charset.py``)
   * - ``context/``
     - Application context singleton for logger configuration
       (``context.py``)
   * - ``core/``
     - Main orchestration: ``process_files()``, ``_load_data()``,
       ``_generate_and_log()``, ``_validate_inputs()``,
       ``_determine_data_source_type()`` (``core.py``)
   * - ``csv/``
     - CSV data loading (``load_csv_data.py``) and validation
       (``validate_csv_data.py``), including streaming variant
   * - ``data/``
     - Universal data loader dispatch: ``load_payment_data()`` routes to
       format-specific loaders (``loader.py``)
   * - ``db/``
     - SQLite loading (``load_db_data.py``), streaming variant
       (``load_db_data_streaming.py``), input validation
       (``validate_db_data.py``)
   * - ``json/``
     - JSON and JSONL loading with streaming support
       (``load_json_data.py``)
   * - ``parquet/``
     - Apache Parquet loading with streaming support
       (``load_parquet_data.py``)
   * - ``security/``
     - Path traversal protection (``validate_path()``), log sanitization
       (``sanitize_for_log()``), ``PathValidationError``, ``SecurityError``
       (``path_validator.py``)
   * - ``validation/``
     - BIC validation (``bic_validator.py``), IBAN validation
       (``iban_validator.py``), JSON schema validation
       (``schema_validator.py``), ``ValidationService`` with configurable
       rules (``service.py``)
   * - ``xml/``
     - XML generation (``generate_xml.py``), XSD validation
       (``validate_via_xsd.py``), namespace registration
       (``register_namespaces.py``), file I/O (``write_xml_to_file.py``,
       ``xml_to_string.py``, ``generate_updated_xml_file_path.py``)
   * - ``templates/``
     - 13 versioned directories, each containing a Jinja2 template
       (``template.xml``), XSD schema (``.xsd``), and sample output (``.xml``)

Top-level modules:

- ``__init__.py`` — Public API exports (``process_files``,
  ``generate_xml_string``, ``PaymentValidationError``, ``DataSourceError``,
  ``__version__``)
- ``__main__.py`` — ``main()`` entry point for ``python -m pacs008``
- ``constants.py`` — ``valid_xml_types`` list, ``BASE_DIR``, ``SCHEMAS_DIR``,
  ``TEMPLATES_DIR``
- ``exceptions.py`` — Exception hierarchy
- ``logging_schema.py`` — Structured logging (``Events``, ``Fields``,
  ``log_event()``)

2. Data Flow
------------

The primary data flow through the system follows this path::

    User Input
        │
        ▼
    process_files(xml_message_type, template, schema, data_source)
        │
        ├─▶ _validate_inputs()          # Check message type + file paths
        │
        ├─▶ _determine_data_source_type()  # Detect format from extension/type
        │
        ├─▶ _load_data()
        │       │
        │       └─▶ load_payment_data()  # Universal dispatcher
        │               │
        │               ├─▶ load_csv_data()      # .csv
        │               ├─▶ load_json_data()     # .json
        │               ├─▶ load_jsonl_data()    # .jsonl
        │               ├─▶ load_db_data()       # .db
        │               ├─▶ load_parquet_data()  # .parquet
        │               └─▶ pass-through         # list/dict
        │
        ├─▶ register_namespaces()       # Version-specific XML namespaces
        │
        └─▶ _generate_and_log()
                │
                └─▶ generate_xml_string(data, message_type, template, schema)
                        │
                        ├─▶ validate_path()              # Path jail check
                        ├─▶ xml_data_preparers[type]()   # Version dispatch
                        ├─▶ Environment(autoescape=True)  # Jinja2 rendering
                        ├─▶ template.render(**data)       # XML string output
                        └─▶ validate_xml_string_via_xsd() # XSD validation
                                │
                                └─▶ defusedxml.ElementTree  # Safe XML parsing
                                        │
                                        └─▶ Validated XML string returned

3. Version Dispatch Strategy
----------------------------

Version-specific XML generation is handled through a dispatch dictionary in
``pacs008/xml/generate_xml.py``:

.. code-block:: python

   xml_data_preparers = {
       "pacs.008.001.01": _prepare_xml_data_v01,
       "pacs.008.001.02": _prepare_xml_data_v02_to_v04,
       "pacs.008.001.03": _prepare_xml_data_v02_to_v04,
       "pacs.008.001.04": _prepare_xml_data_v02_to_v04,
       "pacs.008.001.05": _prepare_xml_data_v05_to_v06,
       "pacs.008.001.06": _prepare_xml_data_v05_to_v06,
       "pacs.008.001.07": _prepare_xml_data_v07,
       "pacs.008.001.08": _prepare_xml_data_v08_to_v09,
       "pacs.008.001.09": _prepare_xml_data_v08_to_v09,
       "pacs.008.001.10": _prepare_xml_data_v10_to_v12,
       "pacs.008.001.11": _prepare_xml_data_v10_to_v12,
       "pacs.008.001.12": _prepare_xml_data_v10_to_v12,
       "pacs.008.001.13": _prepare_xml_data_v13,
   }

**Version groupings and their distinguishing features:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Preparer
     - Versions
     - Distinguishing Features
   * - ``_prepare_xml_data_v01``
     - v01
     - ``<BIC>`` tags, unnumbered ``PrvsInstgAgt``
   * - ``_prepare_xml_data_v02_to_v04``
     - v02, v03, v04
     - BIC/BICFI transition, ``clr_sys_ref`` field
   * - ``_prepare_xml_data_v05_to_v06``
     - v05, v06
     - Full ``<BICFI>``, unnumbered ``PrvsInstgAgt``
   * - ``_prepare_xml_data_v07``
     - v07
     - ``<BICFI>``, numbered ``PrvsInstgAgt1/2/3``
   * - ``_prepare_xml_data_v08_to_v09``
     - v08, v09
     - Adds UETR (Unique End-to-End Transaction Reference)
   * - ``_prepare_xml_data_v10_to_v12``
     - v10, v11, v12
     - Adds mandate information (``MndtRltdInf``)
   * - ``_prepare_xml_data_v13``
     - v13
     - Adds expiry date-time (``XpryDtTm``)

Adding support for future pacs.008 versions requires only:

1. Adding a new version-specific Jinja2 template and XSD schema in
   ``templates/``
2. Implementing a data preparer function (or reusing an existing one)
3. Adding an entry to the ``xml_data_preparers`` dictionary
4. Adding the version string to ``valid_xml_types`` in ``constants.py``

4. Exception Hierarchy
----------------------

::

    Pacs008Error (base)
    ├── PaymentValidationError
    │   ├── InvalidIBANError
    │   │       (fields: message, iban, field, reason)
    │   ├── InvalidBICError
    │   │       (fields: message, bic, field, reason)
    │   └── MissingRequiredFieldError
    │           (fields: message, field, row_number, required_fields)
    ├── XMLGenerationError
    │       (Jinja2 rendering failures, XSD validation failures)
    ├── ConfigurationError
    │       (invalid message types, missing env vars, config file errors)
    ├── DataSourceError
    │       (file not found, DB errors, unsupported formats)
    └── SchemaValidationError (alias: XSDValidationError)
            (fields: message, errors: list)

All exceptions inherit from ``Pacs008Error`` to enable catch-all handling at
API and CLI boundaries.

5. Security Architecture
------------------------

5.1 XML External Entity (XXE) Prevention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``pacs008/xml/validate_via_xsd.py``
- **Control:** All XML parsing uses ``defusedxml.ElementTree`` instead of the
  standard library's ``xml.etree.ElementTree``
- **Protection:** Prevents XML bombs, entity expansion attacks, and external
  entity injection
- **Requirement:** NFR-101

5.2 Path Traversal Protection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``pacs008/security/path_validator.py``
- **Control:** ``validate_path(untrusted_path, must_exist, base_dir)``
  resolves paths with ``os.path.realpath()`` and rejects any path containing
  ``..`` or resolving outside allowed directories
- **Allowed directories:** current working directory, ``tempfile.gettempdir()``,
  ``/var/tmp`` (Unix only)
- **Requirement:** NFR-102

5.3 SQL Input Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``pacs008/db/load_db_data.py``,
  ``pacs008/db/load_db_data_streaming.py``
- **Control:** Table name validation with regex pattern matching; parameterized
  queries where applicable
- **Requirement:** NFR-102

5.4 Log Sanitization
~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``pacs008/security/path_validator.py``,
  ``pacs008/logging_schema.py``
- **Control:** ``sanitize_for_log(user_input, max_length=100)`` strips control
  characters and truncates input before log emission; automatic PII redaction
  for IBAN, BIC, and personal names
- **Requirement:** NFR-103

5.5 Template Injection Prevention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``pacs008/xml/generate_xml.py``
- **Control:** ``Environment(loader=FileSystemLoader(...), autoescape=True)``
- **Protection:** All template variables are auto-escaped, preventing server-side
  template injection (SSTI)
- **Requirement:** NFR-104

5.6 Container Security
~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``Dockerfile``
- **Control:** Application runs as ``appuser`` (non-root), slim base image,
  health check endpoint
- **Requirement:** NFR-105

6. Interface Specifications
---------------------------

6.1 Python API
~~~~~~~~~~~~~~~

.. code-block:: python

   # Primary entry point — full pipeline
   process_files(
       xml_message_type: str,          # e.g. "pacs.008.001.05"
       xml_template_file_path: str,    # path to Jinja2 template
       xsd_schema_file_path: str,      # path to XSD schema
       data_file_path: Union[str, list, dict],  # data source
   ) -> None

   # Low-level — returns XML string without file I/O
   generate_xml_string(
       data: Union[list, dict],
       payment_initiation_message_type: str,
       xml_template_path: str,
       xsd_schema_path: str,
   ) -> str

6.2 CLI
~~~~~~~~

::

   pacs008 -t <message-type> -m <template> -s <schema> -d <data>
           [-o <output-dir>] [--dry-run] [-v]

**Exit codes:** 0 (success), 1 (validation/processing error), 2 (invalid arguments)

6.3 REST API
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Method
     - Endpoint
     - Purpose
   * - GET
     - ``/api/health``
     - Health check
   * - POST
     - ``/api/validate``
     - Validate payment data without generating XML
   * - POST
     - ``/api/generate``
     - Generate XML synchronously
   * - POST
     - ``/api/generate/async``
     - Submit async XML generation job
   * - GET
     - ``/api/status/{job_id}``
     - Poll async job status
   * - DELETE
     - ``/api/jobs/{job_id}``
     - Cancel async job
   * - GET
     - ``/api/download/{job_id}``
     - Download generated XML from completed job

7. Design Decisions and Rationale
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Decision
     - Choice
     - Rationale
   * - Template engine
     - Jinja2
     - Mature, well-documented, supports autoescape; separates XML structure
       from data logic
   * - XML parser
     - defusedxml
     - Drop-in replacement for stdlib with XXE protection; no API changes
       required
   * - Version dispatch
     - Dictionary of functions
     - O(1) lookup, extensible without modifying existing code, each version
       group is isolated
   * - Validation library
     - xmlschema + jsonschema
     - Official XSD/JSON Schema implementations; comprehensive error reporting
   * - CLI framework
     - Click
     - Declarative option/argument syntax, automatic help text, composable
       commands
   * - REST framework
     - FastAPI
     - Async support, automatic OpenAPI docs, Pydantic validation, type hints
   * - Data formats
     - CSV, JSON, JSONL, SQLite, Parquet
     - Covers spreadsheet exports (CSV), API responses (JSON/JSONL), databases
       (SQLite), and analytics pipelines (Parquet)
   * - Streaming support
     - Chunked iterators
     - Bounds memory usage for large datasets; configurable chunk size
   * - Exception hierarchy
     - Single base class
     - Enables catch-all at boundaries while preserving specific error context
   * - Path security
     - Allowlist directories
     - Defense-in-depth; even if application logic is wrong, path jail prevents
       traversal
