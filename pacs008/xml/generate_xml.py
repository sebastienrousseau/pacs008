"""XML generator for pacs.008 FI-to-FI Customer Credit Transfer messages."""

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader

from pacs008.security import validate_path
from pacs008.xml.generate_updated_xml_file_path import (
    generate_updated_xml_file_path,
)
from pacs008.xml.validate_via_xsd import validate_xml_string_via_xsd


def _prepare_xml_data_v01(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.01 (root child: pacs.008.001.01, BIC)."""
    return {
        "msg_id": data[0]["msg_id"],
        "creation_date_time": data[0]["creation_date_time"],
        "nb_of_txs": data[0]["nb_of_txs"],
        "settlement_method": data[0]["settlement_method"],
        "interbank_settlement_date": data[0].get("interbank_settlement_date", ""),
        "transactions": [
            {
                "end_to_end_id": row["end_to_end_id"],
                "tx_id": row.get("tx_id", ""),
                "interbank_settlement_amount": row["interbank_settlement_amount"],
                "interbank_settlement_currency": row["interbank_settlement_currency"],
                "charge_bearer": row.get("charge_bearer", ""),
                "debtor_name": row.get("debtor_name", ""),
                "debtor_account_iban": row.get("debtor_account_iban", ""),
                "debtor_agent_bic": row.get("debtor_agent_bic", ""),
                "creditor_agent_bic": row.get("creditor_agent_bic", ""),
                "creditor_name": row.get("creditor_name", ""),
                "creditor_account_iban": row.get("creditor_account_iban", ""),
                "remittance_information": row.get("remittance_information", ""),
            }
            for row in data
        ],
    }


def _prepare_xml_data_v02_to_v04(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.02-04 (root child: FIToFICstmrCdtTrf, BIC)."""
    return {
        "msg_id": data[0]["msg_id"],
        "creation_date_time": data[0]["creation_date_time"],
        "nb_of_txs": data[0]["nb_of_txs"],
        "settlement_method": data[0]["settlement_method"],
        "interbank_settlement_date": data[0].get("interbank_settlement_date", ""),
        "transactions": [
            {
                "end_to_end_id": row["end_to_end_id"],
                "tx_id": row.get("tx_id", ""),
                "interbank_settlement_amount": row["interbank_settlement_amount"],
                "interbank_settlement_currency": row["interbank_settlement_currency"],
                "charge_bearer": row.get("charge_bearer", ""),
                "debtor_name": row.get("debtor_name", ""),
                "debtor_account_iban": row.get("debtor_account_iban", ""),
                "debtor_agent_bic": row.get("debtor_agent_bic", ""),
                "creditor_agent_bic": row.get("creditor_agent_bic", ""),
                "creditor_name": row.get("creditor_name", ""),
                "creditor_account_iban": row.get("creditor_account_iban", ""),
                "remittance_information": row.get("remittance_information", ""),
            }
            for row in data
        ],
    }


def _prepare_xml_data_v05_to_v07(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.05-07 (BICFI identifiers)."""
    return {
        "msg_id": data[0]["msg_id"],
        "creation_date_time": data[0]["creation_date_time"],
        "nb_of_txs": data[0]["nb_of_txs"],
        "settlement_method": data[0]["settlement_method"],
        "interbank_settlement_date": data[0].get("interbank_settlement_date", ""),
        "transactions": [
            {
                "end_to_end_id": row["end_to_end_id"],
                "tx_id": row.get("tx_id", ""),
                "interbank_settlement_amount": row["interbank_settlement_amount"],
                "interbank_settlement_currency": row["interbank_settlement_currency"],
                "charge_bearer": row.get("charge_bearer", ""),
                "debtor_name": row.get("debtor_name", ""),
                "debtor_account_iban": row.get("debtor_account_iban", ""),
                "debtor_agent_bic": row.get("debtor_agent_bic", ""),
                "creditor_agent_bic": row.get("creditor_agent_bic", ""),
                "creditor_name": row.get("creditor_name", ""),
                "creditor_account_iban": row.get("creditor_account_iban", ""),
                "remittance_information": row.get("remittance_information", ""),
                "instd_amount": row.get("instd_amount", ""),
                "instd_currency": row.get("instd_currency", ""),
            }
            for row in data
        ],
    }


def _prepare_xml_data_v08_to_v09(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.08-09 (BICFI + UETR)."""
    base = _prepare_xml_data_v05_to_v07(data)
    for i, row in enumerate(data):
        base["transactions"][i]["uetr"] = row.get("uetr", "")
    return base


def _prepare_xml_data_v10_to_v12(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.10-12 (BICFI + UETR + MndtRltdInf)."""
    base = _prepare_xml_data_v08_to_v09(data)
    for i, row in enumerate(data):
        base["transactions"][i]["mandate_id"] = row.get("mandate_id", "")
    return base


def _prepare_xml_data_v13(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.13 (all above + XpryDtTm)."""
    base = _prepare_xml_data_v10_to_v12(data)
    base["expiry_date_time"] = data[0].get("expiry_date_time", "")
    return base


def generate_xml_string(
    data: list[dict[str, Any]],
    payment_initiation_message_type: str,
    xml_template_path: str,
    xsd_schema_path: str,
) -> str:
    """Generate ISO 20022 pacs.008 XML content as a string."""
    xml_data_preparers = {
        "pacs.008.001.01": _prepare_xml_data_v01,
        "pacs.008.001.02": _prepare_xml_data_v02_to_v04,
        "pacs.008.001.03": _prepare_xml_data_v02_to_v04,
        "pacs.008.001.04": _prepare_xml_data_v02_to_v04,
        "pacs.008.001.05": _prepare_xml_data_v05_to_v07,
        "pacs.008.001.06": _prepare_xml_data_v05_to_v07,
        "pacs.008.001.07": _prepare_xml_data_v05_to_v07,
        "pacs.008.001.08": _prepare_xml_data_v08_to_v09,
        "pacs.008.001.09": _prepare_xml_data_v08_to_v09,
        "pacs.008.001.10": _prepare_xml_data_v10_to_v12,
        "pacs.008.001.11": _prepare_xml_data_v10_to_v12,
        "pacs.008.001.12": _prepare_xml_data_v10_to_v12,
        "pacs.008.001.13": _prepare_xml_data_v13,
    }

    try:
        xml_template_path = validate_path(xml_template_path)
    except Exception as e:
        raise ValueError(f"Invalid template path: {e}") from e

    try:
        xsd_schema_path = validate_path(xsd_schema_path)
    except Exception as e:
        raise ValueError(f"Invalid schema path: {e}") from e

    if payment_initiation_message_type not in xml_data_preparers:
        raise ValueError(
            f"Invalid XML message type: {payment_initiation_message_type}"
        )

    if not data:
        raise ValueError("No data to process - data list is empty")

    preparer = xml_data_preparers[payment_initiation_message_type]
    xml_data = preparer(data)

    template_dir = os.path.dirname(xml_template_path)
    template_file = os.path.basename(xml_template_path)
    loader_path = template_dir if template_dir else "."

    env = Environment(loader=FileSystemLoader(loader_path), autoescape=True)
    template = env.get_template(template_file)

    xml_content = template.render(**xml_data)

    is_valid = validate_xml_string_via_xsd(xml_content, xsd_schema_path)

    if not is_valid:
        raise RuntimeError(
            f"Generated XML failed validation against {xsd_schema_path}"
        )

    return xml_content


def generate_xml(
    data: list[dict[str, Any]],
    payment_initiation_message_type: str,
    xml_file_path: str,
    xsd_file_path: str,
) -> None:
    """Generates an ISO 20022 pacs.008 XML file from input data."""
    xml_content = generate_xml_string(
        data, payment_initiation_message_type, xml_file_path, xsd_file_path
    )

    updated_xml_file_path = generate_updated_xml_file_path(
        xml_file_path, payment_initiation_message_type
    )

    try:
        safe_xml_path = validate_path(updated_xml_file_path)
    except Exception as e:
        raise ValueError(f"Path validation failed: {e}") from e

    cwd_prefix = str(os.path.realpath(os.getcwd()))
    if not safe_xml_path.startswith(cwd_prefix + os.sep):
        raise ValueError(
            f"Output path outside working directory: {safe_xml_path}"
        )

    with open(safe_xml_path, "w", encoding="utf-8") as xml_file:
        xml_file.write(xml_content)

    print(f"A new XML file has been created at `{safe_xml_path}`")
    print(f"The XML has been validated against `{xsd_file_path}`")
