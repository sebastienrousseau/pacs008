.. _dhf-index:

=======================================
Design History File — Master Index
=======================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-001
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - pacs008 Engineering
   * - Status
     - Released
   * - Classification
     - Internal

Purpose
-------

This Design History File (DHF) provides ISO 13485:2016-equivalent documentation
rigor for the **pacs008** library — a Python library for generating ISO 20022
pacs.008 FI-to-FI Customer Credit Transfer XML messages.

While pacs008 is financial infrastructure software rather than a medical device,
this DHF applies the same systematic design control discipline required by
ISO 13485:2016 clause 7.3 to demonstrate that the software was developed under
a controlled, traceable, and verified process. This approach satisfies
institutional audit requirements and establishes readiness for regulated
deployment environments.

Scope
-----

- **Product:** pacs008 Python library
- **Version:** 0.0.1
- **Message standard:** ISO 20022 pacs.008.001.01 through pacs.008.001.13 (all 13 versions)
- **IEC 62304 safety classification:** Class A (voluntary Class C processes applied)

Document Set
------------

.. list-table::
   :header-rows: 1
   :widths: 10 15 45 30

   * - #
     - ID
     - Document
     - ISO 13485 Clause
   * - 1
     - DHF-001
     - :ref:`dhf-index` (this document)
     - 7.3.10 (DHF overview)
   * - 2
     - DHF-002
     - :ref:`dhf-design-development-plan`
     - 7.3.1, 7.3.2
   * - 3
     - DHF-003
     - :ref:`dhf-software-requirements`
     - 7.3.3
   * - 4
     - DHF-004
     - :ref:`dhf-software-architecture`
     - 7.3.4
   * - 5
     - DHF-005
     - :ref:`dhf-risk-management`
     - 7.3.4, ISO 14971, IEC 62304
   * - 6
     - DHF-006
     - :ref:`dhf-verification-validation`
     - 7.3.5, 7.3.6, 7.3.7
   * - 7
     - DHF-007
     - :ref:`dhf-traceability-matrix`
     - 7.3.10
   * - 8
     - DHF-008
     - :ref:`dhf-design-review-change-control`
     - 7.3.4, 7.3.9
   * - 9
     - DHF-009
     - :ref:`dhf-configuration-management`
     - 7.3.8, 4.2.3

.. toctree::
   :maxdepth: 2
   :caption: DHF Documents

   design-development-plan
   software-requirements-specification
   software-architecture-document
   risk-management-file
   verification-validation-plan
   traceability-matrix
   design-review-change-control
   configuration-management-design-transfer

Standards Compliance Cross-Reference
-------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Standard
     - Clause
     - DHF Coverage
   * - ISO 13485:2016
     - 7.3.1
     - DHF-002 Design and Development Planning
   * - ISO 13485:2016
     - 7.3.2
     - DHF-002 Design and Development Inputs
   * - ISO 13485:2016
     - 7.3.3
     - DHF-003 Software Requirements Specification
   * - ISO 13485:2016
     - 7.3.4
     - DHF-004 Software Architecture, DHF-005 Risk Management
   * - ISO 13485:2016
     - 7.3.5
     - DHF-006 Verification and Validation Plan
   * - ISO 13485:2016
     - 7.3.6
     - DHF-006 Design Validation
   * - ISO 13485:2016
     - 7.3.7
     - DHF-008 Design Review and Change Control
   * - ISO 13485:2016
     - 7.3.8
     - DHF-009 Configuration Management and Design Transfer
   * - ISO 13485:2016
     - 7.3.9
     - DHF-008 Design Changes
   * - ISO 13485:2016
     - 7.3.10
     - DHF-001 (this document), DHF-007 Traceability Matrix
   * - ISO 13485:2016
     - 4.2.3
     - DHF-009 Document Control
   * - ISO 14971:2019
     - All
     - DHF-005 Risk Management File
   * - IEC 62304:2006+A1
     - All
     - DHF-002 through DHF-009

Approval Signatures
-------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Role
     - Name
     - Signature
     - Date
   * - Lead Engineer
     -
     -
     -
   * - Quality Assurance
     -
     -
     -
   * - Regulatory Affairs
     -
     -
     -
