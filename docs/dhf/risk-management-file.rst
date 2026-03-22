.. _dhf-risk-management:

============================================
Risk Management File
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-005
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
   * - Additional Standards
     - ISO 14971:2019 (Risk Management), IEC 62304:2006+A1 (Software Lifecycle)

1. IEC 62304 Safety Classification
-----------------------------------

**Classification: Class A** (no contribution to hazardous situation)

The pacs008 library is a data transformation tool that generates XML messages
from structured input. It does not control physical processes, medical devices,
or safety-critical systems. Under IEC 62304, it is classified as **Class A**.

However, the project voluntarily applies **Class C-level processes** to
demonstrate the highest level of software engineering rigor:

- Full branch coverage (100%)
- Formal risk analysis with mitigations
- Static analysis (mypy strict, bandit SAST)
- Signed commits with full traceability
- Structured design documentation (this DHF)

This voluntary elevation provides audit readiness for deployment in regulated
financial environments and institutional settings.

2. Risk Analysis Methodology
-----------------------------

Risks are assessed using an ISO 14971-style framework:

- **Severity:** Impact if the risk is realized (Low / Medium / High / Critical)
- **Probability:** Likelihood of occurrence given normal use (Rare / Unlikely /
  Possible / Likely)
- **Risk Level:** Combination of severity and probability (Low / Medium / High)
- **Mitigation:** Engineering control implemented to reduce risk
- **Residual Risk:** Risk level after mitigation is applied and verified

3. Risk Register
-----------------

.. list-table::
   :header-rows: 1
   :widths: 8 20 12 12 12 36

   * - ID
     - Risk Description
     - Severity
     - Probability
     - Initial Risk
     - Mitigation
   * - R-001
     - Generated XML is invalid and rejected by receiving financial
       institution
     - High
     - Possible
     - High
     - All generated XML is validated against official XSD schemas via
       ``validate_xml_string_via_xsd()`` before output. Generation fails
       if validation fails.
   * - R-002
     - XML External Entity (XXE) injection via crafted input data
     - Critical
     - Unlikely
     - High
     - All XML parsing uses ``defusedxml.ElementTree`` instead of stdlib.
       Entity expansion, external entities, and DTD processing are disabled.
   * - R-003
     - Path traversal attack reads or writes files outside intended
       directories
     - Critical
     - Unlikely
     - High
     - ``validate_path()`` resolves all paths with ``os.path.realpath()``,
       rejects ``..`` components, and enforces an allowlist of base
       directories (cwd, tempdir, ``/var/tmp``).
   * - R-004
     - SQL injection via crafted table name in SQLite loader
     - High
     - Unlikely
     - Medium
     - Table name validated with regex pattern matching. Parameterized
       queries used where applicable.
   * - R-005
     - Invalid BIC or IBAN codes in payment data produce non-compliant
       messages
     - High
     - Possible
     - High
     - ``validate_bic()`` checks ISO 9362 format rules.
       ``validate_iban()`` verifies ISO 7064 mod-97-10 checksum. Both are
       invoked by ``ValidationService`` before generation.
   * - R-006
     - Non-SWIFT characters in payment fields cause message rejection by
       SWIFT network
     - Medium
     - Possible
     - Medium
     - SWIFT charset validation (Z/z character set) in
       ``compliance/swift_charset.py``. Transliteration for recoverable
       characters. Compliance report generation for violations.
   * - R-007
     - Field length overflow causes SWIFT message truncation or rejection
     - Medium
     - Possible
     - Medium
     - Field length enforcement in ``compliance/swift_charset.py`` checks
       all applicable payment fields against SWIFT-defined limits.
   * - R-008
     - Invalid or unsupported pacs.008 version string causes unexpected
       behavior
     - Medium
     - Unlikely
     - Low
     - ``valid_xml_types`` allowlist in ``constants.py`` defines exactly 13
       accepted version strings. ``ConfigurationError`` raised for any
       value not in the list.
   * - R-009
     - Log injection via crafted user input embeds malicious content in
       log files
     - Medium
     - Unlikely
     - Low
     - ``sanitize_for_log(user_input, max_length=100)`` strips control
       characters (newlines, carriage returns, null bytes) and truncates
       before log emission.
   * - R-010
     - Dependency vulnerability in third-party package introduces security
       flaw
     - High
     - Unlikely
     - Medium
     - Dependencies pinned to specific versions in ``pyproject.toml``.
       ``safety`` scanner in dev dependencies. Dependabot / automated
       alerts on GitHub.
   * - R-011
     - Schema mismatch between Jinja2 template and XSD causes silent data
       loss or generation of non-conformant XML
     - High
     - Rare
     - Medium
     - 13 JSON schemas + 13 XSD schemas maintained in ``templates/``
       directory. Gold master tests (``test_gold_master.py``) validate
       end-to-end for all 13 versions against known-good reference outputs.
   * - R-012
     - Server-side template injection (SSTI) via crafted payment data
       fields
     - Critical
     - Unlikely
     - High
     - Jinja2 ``Environment`` created with ``autoescape=True``. All
       template variables are automatically HTML-escaped before rendering.

4. Risk Control Verification
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Risk ID
     - Mitigation Control
     - Verification Test File(s)
     - Result
   * - R-001
     - XSD validation of all generated XML
     - ``test_xsd_validation.py``, ``test_generate_xml.py``,
       ``test_gold_master.py``, ``test_enterprise_xsd.py``
     - Pass
   * - R-002
     - defusedxml for all XML parsing
     - ``test_xsd_validation.py`` (XXE test cases)
     - Pass
   * - R-003
     - Path validation with directory jail
     - ``test_path_validator.py``
     - Pass
   * - R-004
     - SQL input validation
     - ``test_db_loader.py``
     - Pass
   * - R-005
     - BIC + IBAN format and checksum validation
     - ``test_bic_validator.py``, ``test_iban_validator.py``
     - Pass
   * - R-006
     - SWIFT charset validation and transliteration
     - ``test_compliance.py``
     - Pass
   * - R-007
     - SWIFT field length enforcement
     - ``test_compliance.py``
     - Pass
   * - R-008
     - Version string allowlist
     - ``test_constants.py``, ``test_version_matrix.py``
     - Pass
   * - R-009
     - Log sanitization
     - ``test_path_validator.py``, ``test_logging_schema.py``
     - Pass
   * - R-010
     - Dependency pinning + safety scanner
     - CI pipeline ``security`` job (Bandit + safety)
     - Pass
   * - R-011
     - Gold master tests for all 13 versions
     - ``test_gold_master.py``, ``test_version_matrix.py``
     - Pass
   * - R-012
     - Jinja2 autoescape=True
     - ``test_generate_xml.py``
     - Pass

5. Residual Risk Assessment
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 25 25 20 20

   * - Risk ID
     - Initial Risk
     - Mitigation Effectiveness
     - Residual Risk
     - Acceptable?
   * - R-001
     - High
     - XSD validation is deterministic and comprehensive
     - Low
     - Yes
   * - R-002
     - High
     - defusedxml completely disables XXE attack surface
     - Low
     - Yes
   * - R-003
     - High
     - Path jail with realpath resolution eliminates traversal
     - Low
     - Yes
   * - R-004
     - Medium
     - Regex validation restricts input to safe characters
     - Low
     - Yes
   * - R-005
     - High
     - ISO-standard validation algorithms are well-proven
     - Low
     - Yes
   * - R-006
     - Medium
     - Charset validation covers full SWIFT character set
     - Low
     - Yes
   * - R-007
     - Medium
     - Length limits enforced before generation
     - Low
     - Yes
   * - R-008
     - Low
     - Allowlist is exhaustive for all published versions
     - Low
     - Yes
   * - R-009
     - Low
     - Control character stripping + truncation
     - Low
     - Yes
   * - R-010
     - Medium
     - Pinning + scanning reduces window of exposure
     - Low
     - Yes
   * - R-011
     - Medium
     - Gold master tests catch any schema drift
     - Low
     - Yes
   * - R-012
     - High
     - Autoescape is a framework-level guarantee
     - Low
     - Yes

**Overall residual risk: Low.** All identified risks have been mitigated to an
acceptable level through engineering controls that are verified by automated
tests and CI pipeline checks.
