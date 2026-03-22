pacs008 Documentation
=====================

**pacs008** is a Python library for generating ISO 20022 pacs.008 FI-to-FI
Customer Credit Transfer XML messages. It supports all 13 versions
(pacs.008.001.01 through pacs.008.001.13).

Quick Start
-----------

.. code-block:: python

   from pacs008 import generate_xml_string

   data = [{
       "msg_id": "MSG-001",
       "creation_date_time": "2026-01-15T10:30:00",
       "nb_of_txs": "1",
       "settlement_method": "CLRG",
       "interbank_settlement_date": "2026-01-15",
       "end_to_end_id": "E2E-001",
       "tx_id": "TX-001",
       "interbank_settlement_amount": "25000.00",
       "interbank_settlement_currency": "EUR",
       "charge_bearer": "SHAR",
       "debtor_name": "Acme Corp",
       "debtor_agent_bic": "DEUTDEFF",
       "creditor_agent_bic": "COBADEFF",
       "creditor_name": "Widget Industries",
   }]

   xml = generate_xml_string(
       data,
       "pacs.008.001.05",
       "pacs008/templates/pacs.008.001.05/template.xml",
       "pacs008/templates/pacs.008.001.05/pacs.008.001.05.xsd",
   )
   print(xml)

Design History File
-------------------

.. toctree::
   :maxdepth: 2
   :caption: Design History File (DHF)

   dhf/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
