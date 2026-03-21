#!/usr/bin/env python3
"""Example: SWIFT compliance cleansing before XML generation.

Usage:
    python examples/swift_compliance.py

Demonstrates how to cleanse payment data containing non-SWIFT characters
and oversized fields before generating XML.
"""

from pacs008.compliance import cleanse_data, cleanse_data_with_report

# Raw data with SWIFT compliance issues
raw_data = [
    {
        "msg_id": "X" * 50,  # Too long (max 35)
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "end_to_end_id": "E2E-001",
        "tx_id": "TX-001",
        "interbank_settlement_amount": "5000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Müller & Söhne™ GmbH",  # Non-SWIFT chars
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "García Café SL",  # Accented chars
        "remittance_information": "Invoice™ #123 — €500 payment",
    }
]

# Option 1: Simple cleanse
clean = cleanse_data(raw_data)
print("=== Simple Cleanse ===")
print(f"  debtor_name: {raw_data[0]['debtor_name']!r}")
print(f"           -> {clean[0]['debtor_name']!r}")
print(f"  msg_id length: {len(raw_data[0]['msg_id'])} -> {len(clean[0]['msg_id'])}")
print()

# Option 2: Cleanse with detailed report
clean, report = cleanse_data_with_report(raw_data)
print("=== Cleanse with Report ===")
print(f"  {report.summary()}")
print(f"  Violations: {report.violation_count}")
print(f"  Rows modified: {report.rows_modified}/{report.rows_processed}")
for v in report.violations:
    print(f"    - {v.field}: {v.violation_type} — {v.message}")
