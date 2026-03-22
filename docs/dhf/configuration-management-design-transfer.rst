.. _dhf-configuration-management:

=============================================
Configuration Management and Design Transfer
=============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-009
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.8 (Design and Development Transfer), 4.2.3 (Control of Documents)

1. Version Control
------------------

1.1 Repository
~~~~~~~~~~~~~~~

- **System:** Git
- **Hosting:** GitHub
- **Repository:** pacs008 (private)
- **Default branch:** main

1.2 Branching Strategy
~~~~~~~~~~~~~~~~~~~~~~~

- **main** — Production-ready code. All CI checks must pass before merge.
- **feature/** — Feature development branches. Created from main, merged
  back via pull request.
- **fix/** — Bug fix branches. Created from main, merged back via pull
  request.

All branches must pass the full CI pipeline before merge. Direct pushes to
main are prohibited.

2. Commit Policy
-----------------

2.1 Signed Commits
~~~~~~~~~~~~~~~~~~~~

All commits **must** be cryptographically signed using GPG or SSH keys. This
provides:

- **Authentication:** Verifies the identity of the committer
- **Integrity:** Guarantees the commit has not been tampered with
- **Non-repudiation:** Creates an auditable chain of authorship

Unsigned commits are rejected by repository policy.

2.2 Commit Message Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Commits follow conventional commit format:

::

   <type>(<scope>): <description>

   [optional body]

   [optional footer]

**Types:** ``feat``, ``fix``, ``docs``, ``style``, ``refactor``, ``perf``,
``test``, ``build``, ``ci``, ``chore``

**Examples:**

::

   feat(xml): add pacs.008.001.13 support with expiry datetime
   fix(validation): correct IBAN checksum for edge case
   test(gold-master): add v13 reference fixture

3. Pre-commit Hooks
--------------------

The ``.pre-commit-config.yaml`` file defines 13 hooks that run before every
commit:

.. list-table::
   :header-rows: 1
   :widths: 5 25 70

   * - #
     - Hook
     - Purpose
   * - 1
     - trailing-whitespace
     - Removes trailing whitespace from all files
   * - 2
     - end-of-file-fixer
     - Ensures every file ends with a single newline
   * - 3
     - check-yaml
     - Validates YAML file syntax
   * - 4
     - check-json
     - Validates JSON file syntax
   * - 5
     - check-toml
     - Validates TOML file syntax
   * - 6
     - check-merge-conflict
     - Detects unresolved merge conflict markers
   * - 7
     - check-added-large-files
     - Rejects files larger than 500 KB
   * - 8
     - mixed-line-ending
     - Enforces LF line endings (``--fix=lf``)
   * - 9
     - detect-private-key
     - Prevents accidental commit of private keys
   * - 10
     - ruff (lint)
     - Code linting with auto-fix (``--fix``)
   * - 11
     - ruff-format
     - Consistent code formatting
   * - 12
     - black
     - Code style enforcement (line-length=79)
   * - 13
     - mypy
     - Static type checking (strict mode, pacs008/ only)

4. Configuration Items
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Item
     - Type
     - Location
   * - Source code
     - Python
     - ``pacs008/`` (43 modules in 14 packages)
   * - Test suite
     - Python
     - ``tests/`` (36 test files, 1,417 test cases)
   * - Jinja2 templates
     - XML
     - ``pacs008/templates/pacs.008.001.XX/template.xml`` (13 files)
   * - XSD schemas
     - XML Schema
     - ``pacs008/templates/pacs.008.001.XX/pacs.008.001.XX.xsd`` (13 files)
   * - Reference XML
     - XML
     - ``pacs008/templates/pacs.008.001.XX/pacs.008.001.XX.xml`` (13 files)
   * - Project metadata
     - TOML
     - ``pyproject.toml``
   * - CI pipeline
     - YAML
     - ``.github/workflows/ci.yml``
   * - Pre-commit config
     - YAML
     - ``.pre-commit-config.yaml``
   * - Dockerfile
     - Dockerfile
     - ``Dockerfile``
   * - Documentation
     - RST
     - ``docs/`` (Sphinx source)
   * - Changelog
     - Markdown
     - ``CHANGELOG.md``
   * - DHF documents
     - RST
     - ``docs/dhf/`` (9 files, this document set)

5. Baseline Definition
-----------------------

**Baseline: v0.0.1** (2026-03-21)

This baseline represents the initial release of the pacs008 library with the
following verified characteristics:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Characteristic
     - Value
   * - pacs.008 versions supported
     - 13 (001.01 through 001.13)
   * - Test count
     - 1,417
   * - Branch coverage
     - 100%
   * - Bandit SAST findings
     - 0
   * - mypy strict errors
     - 0
   * - ruff/black violations
     - 0
   * - Pre-commit hooks
     - 13 (all passing)
   * - CI matrix configurations
     - 14 (12 test + 1 lint + 1 security)
   * - Python versions
     - 3.9, 3.10, 3.11, 3.12
   * - Operating systems
     - Linux (Ubuntu), macOS, Windows
   * - Data source formats
     - 5 (CSV, JSON, JSONL, SQLite, Parquet)
   * - Risk mitigations
     - 12 (all verified, all residual risk Low)

The baseline is tagged in Git as ``v0.0.1`` and represents a complete,
verified, and traceable release.

6. Release Process Checklist
-----------------------------

Before any release, the following steps must be completed:

.. list-table::
   :header-rows: 1
   :widths: 5 65 30

   * - #
     - Step
     - Verification
   * - 1
     - All CI pipeline jobs pass (test, lint, security, smoke)
     - GitHub Actions green status
   * - 2
     - Branch coverage >= 99%
     - ``--cov-fail-under=99`` in pytest output
   * - 3
     - Bandit SAST reports zero findings
     - CI security job output
   * - 4
     - mypy strict reports zero errors
     - CI lint job output
   * - 5
     - All 13 gold master tests pass
     - ``test_gold_master.py`` output
   * - 6
     - All pre-commit hooks pass
     - ``pre-commit run --all-files``
   * - 7
     - CHANGELOG.md updated with release notes
     - Manual review
   * - 8
     - Version number updated in ``pyproject.toml``
     - Manual review
   * - 9
     - DHF documents updated if requirements, architecture, or risks changed
     - Manual review
   * - 10
     - Git tag created and signed
     - ``git tag -s vX.Y.Z``
   * - 11
     - Package built and tested locally
     - ``poetry build && pip install dist/*.whl``
   * - 12
     - Package published to PyPI
     - ``poetry publish``
   * - 13
     - Docker image built and tested
     - ``docker build -t pacs008:vX.Y.Z .``
   * - 14
     - Release notes published on GitHub
     - GitHub Releases page

7. Deployment Architecture
---------------------------

The pacs008 library is distributed through three channels:

7.1 PyPI Package
~~~~~~~~~~~~~~~~~

- **Build:** ``poetry build`` produces source distribution and wheel
- **Publish:** ``poetry publish`` uploads to PyPI
- **Install:** ``pip install pacs008``
- **Dependencies:** Resolved from ``pyproject.toml`` at install time

7.2 Docker Container
~~~~~~~~~~~~~~~~~~~~~

- **Base image:** ``python:3.12-slim``
- **Build:** ``docker build -t pacs008:latest .``
- **Port:** 8000 (REST API via uvicorn)
- **User:** ``appuser`` (non-root)
- **Health check:** HTTP GET to ``/api/health`` every 30 seconds
- **Startup:** ``python -m uvicorn pacs008.api.app:app --host 0.0.0.0 --port 8000``

7.3 Source Installation
~~~~~~~~~~~~~~~~~~~~~~~~

- **Clone:** ``git clone <repository>``
- **Install:** ``poetry install``
- **Verify:** ``poetry run pytest``
- **Usage:** Import ``pacs008`` directly or run CLI/REST API
