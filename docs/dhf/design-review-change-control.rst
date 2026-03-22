.. _dhf-design-review-change-control:

============================================
Design Review and Change Control
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-008
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.4 (Design and Development Review), 7.3.9 (Design Changes)

1. Design Review Records
-------------------------

1.1 DR-001: Architecture Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :stub-columns: 1

   * - Review ID
     - DR-001
   * - Date
     - 2026-03-21
   * - Phase
     - Phase 1 (Core XML Generation)
   * - Scope
     - Module architecture, version dispatch strategy, data flow,
       exception hierarchy
   * - Participants
     - Lead Engineer, Quality Assurance
   * - Findings
     - (a) 14-package modular architecture provides clear separation of
       concerns. (b) Version dispatch via dictionary enables O(1) lookup
       and extensibility without modifying existing code. (c) Exception
       hierarchy with single base class supports catch-all handling at API
       and CLI boundaries.
   * - Disposition
     - Approved. Architecture supports all 13 pacs.008 versions with a
       consistent pattern for adding future versions.
   * - Action Items
     - None. Proceed to Phase 2.

1.2 DR-002: Security Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :stub-columns: 1

   * - Review ID
     - DR-002
   * - Date
     - 2026-03-21
   * - Phase
     - Phase 6 (Security Hardening)
   * - Scope
     - XXE prevention, path traversal protection, SQL input validation,
       log sanitization, template injection prevention, container security
   * - Participants
     - Lead Engineer, Security Reviewer
   * - Findings
     - (a) defusedxml completely disables XXE attack surface — verified by
       security-marked tests. (b) Path jail restricts file access to cwd,
       tempdir, and /var/tmp with realpath resolution. (c) Jinja2
       autoescape=True prevents SSTI. (d) Log sanitization strips control
       characters before emission. (e) Docker runs as non-root user.
       (f) Bandit SAST reports zero findings.
   * - Disposition
     - Approved. All OWASP Top 10 relevant attack vectors are mitigated
       with defense-in-depth controls.
   * - Action Items
     - None. All security controls verified by automated tests.

1.3 DR-003: SWIFT Compliance Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :stub-columns: 1

   * - Review ID
     - DR-003
   * - Date
     - 2026-03-21
   * - Phase
     - Phase 4 (SWIFT Compliance)
   * - Scope
     - Charset validation (Z/z set), field length enforcement,
       transliteration, BIC/IBAN validation, version-specific features
   * - Participants
     - Lead Engineer, Domain Expert
   * - Findings
     - (a) SWIFT charset validation covers the full Z and z character sets
       per SWIFT standards. (b) Field length limits enforced for all
       applicable fields. (c) BIC validation follows ISO 9362 format rules.
       (d) IBAN validation implements ISO 7064 mod-97-10 checksum.
       (e) All 13 versions correctly implement version-specific features
       (BIC/BICFI transition, UETR, mandate, expiry).
   * - Disposition
     - Approved. SWIFT compliance module meets ISO 20022 message standards.
   * - Action Items
     - None. Gold master tests verify compliance for all 13 versions.

1.4 DR-004: API and Interface Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :stub-columns: 1

   * - Review ID
     - DR-004
   * - Date
     - 2026-03-21
   * - Phase
     - Phase 5 (Interface Layer)
   * - Scope
     - Python API (process_files, generate_xml_string), CLI (Click),
       REST API (FastAPI), async job management
   * - Participants
     - Lead Engineer, Quality Assurance
   * - Findings
     - (a) Python API exposes two clean entry points: ``process_files()``
       for full pipeline and ``generate_xml_string()`` for string-only
       output. (b) CLI provides all necessary options with proper
       validation and exit codes. (c) REST API includes health check,
       sync/async generation, and job management. (d) Pydantic models
       enforce request/response validation at the API boundary.
   * - Disposition
     - Approved. All three interfaces provide appropriate access to core
       functionality with proper input validation.
   * - Action Items
     - None. Interface tests cover all endpoints and options.

2. Change Control Log
---------------------

Design changes are tracked in ``CHANGELOG.md`` using Keep a Changelog format.
The following table summarizes changes relevant to the DHF:

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Version
     - Date
     - Summary
   * - 0.0.1
     - 2026-03-21
     - Initial release. Support for all 13 ISO 20022 pacs.008 versions.
       Multi-source data ingestion (CSV, JSON, JSONL, SQLite, Parquet).
       Jinja2 template engine with XSD validation. SWIFT compliance module.
       FastAPI REST API with async job management. Click CLI. BIC and IBAN
       validators. JSON schema validation. Path traversal protection.
       Security hardening. 1,400+ tests with 100% coverage. Gold master
       fixtures for all 13 versions. Cross-platform CI.

3. Design Change Process
------------------------

All design changes follow this procedure:

3.1 Change Request
~~~~~~~~~~~~~~~~~~~

1. Change is proposed via GitHub Issue or Pull Request
2. Change request includes: description, rationale, affected components,
   risk assessment

3.2 Impact Analysis
~~~~~~~~~~~~~~~~~~~~

1. Identify affected modules, tests, and documentation
2. Review requirements traceability (DHF-007) for impacted requirements
3. Review risk register (DHF-005) for new or modified risks
4. Determine if change requires design review

3.3 Implementation
~~~~~~~~~~~~~~~~~~~

1. Create feature branch from main
2. Implement change following coding standards (ruff, black, mypy strict)
3. Add or update tests to maintain >= 99% branch coverage
4. Update documentation if affected

3.4 Verification
~~~~~~~~~~~~~~~~~

1. All pre-commit hooks pass (13 hooks)
2. Full CI pipeline passes (test, lint, security, smoke jobs)
3. Branch coverage >= 99% maintained
4. Bandit SAST reports zero findings
5. Gold master tests pass (if XML generation affected)

3.5 Review and Approval
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Pull request reviewed by at least one team member
2. Design review conducted if change affects architecture, security, or
   compliance (DR record created)
3. Change merged via signed commit

3.6 Post-Change Activities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Update CHANGELOG.md with change summary
2. Update DHF documents if requirements, architecture, risks, or
   traceability are affected
3. Tag release if change is included in a version release
