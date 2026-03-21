#!/usr/bin/env python3
"""Example: Generate a pacs.008 XML file from Python data.

Usage:
    python examples/generate_xml.py

This creates a pacs.008.001.05 XML message with a single EUR transfer.
"""

from pathlib import Path

from pacs008 import generate_xml_string

# Payment data — one dict per transaction
data = [
    {
        "msg_id": "MSG-EXAMPLE-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "end_to_end_id": "E2E-INV-2026-001",
        "tx_id": "TX-001",
        "interbank_settlement_amount": "25000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Acme Corp GmbH",
        "debtor_account_iban": "DE89370400440532013000",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Widget Industries SA",
        "creditor_account_iban": "FR7630006000011234567890189",
        "remittance_information": "Invoice INV-2026-001",
    }
]

# Paths to template and XSD
version = "pacs.008.001.05"
base = Path(__file__).resolve().parent.parent / "pacs008" / "templates" / version
template = str(base / "template.xml")
xsd = str(base / f"{version}.xsd")

# Generate XML
xml = generate_xml_string(data, version, template, xsd)

# Write to file
output = Path("output_pacs008.xml")
output.write_text(xml, encoding="utf-8")
print(f"Generated: {output.resolve()}")
print(f"Size: {len(xml)} bytes")
