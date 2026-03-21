"""XML generator for pacs.008 FI-to-FI Customer Credit Transfer messages."""

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader

from pacs008.security import validate_path
from pacs008.xml.generate_updated_xml_file_path import (
    generate_updated_xml_file_path,
)
from pacs008.xml.validate_via_xsd import validate_xml_string_via_xsd

# ── Optional field names common to all versions ──────────────────────

_HEADER_OPTIONAL = [
    "btch_bookg",
    "ctrl_sum",
    "ttl_intrbank_sttlm_amt",
    "ttl_intrbank_sttlm_ccy",
    "instg_agt_bic",
    "instd_agt_bic",
]

_TX_COMMON = [
    "instr_id",
    "interbank_settlement_date",
    "instd_amount",
    "instd_currency",
    "xchg_rate",
    "chrgs_inf_amt",
    "chrgs_inf_ccy",
    "chrgs_inf_agt_bic",
    "intermediary_agent1_bic",
    "intermediary_agent2_bic",
    "intermediary_agent3_bic",
    "ultimate_debtor_name",
    "ultimate_creditor_name",
    "instr_for_cdtr_agt_cd",
    "instr_for_cdtr_agt_inf",
    "instr_for_nxt_agt_inf",
    "purpose_cd",
    "rgltry_rptg_dbt_cdt_rptg_ind",
    "rgltry_rptg_authrty_nm",
    "rgltry_rptg_authrty_ctry",
    "rgltry_rptg_cd",
    "rgltry_rptg_inf",
    "pmt_tp_inf_instr_prty",
    "pmt_tp_inf_svc_lvl_cd",
    "pmt_tp_inf_lcl_instrm_cd",
    "pmt_tp_inf_ctgy_purp_cd",
    "sttlm_prty",
]


def _build_header(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Build GrpHdr data from the first row."""
    first = data[0]
    hdr: dict[str, Any] = {
        "msg_id": first["msg_id"],
        "creation_date_time": first["creation_date_time"],
        "nb_of_txs": first["nb_of_txs"],
        "settlement_method": first["settlement_method"],
        "interbank_settlement_date": first.get(
            "interbank_settlement_date", ""
        ),
    }
    for key in _HEADER_OPTIONAL:
        hdr[key] = first.get(key, "")
    return hdr


def _build_tx_base(row: dict[str, Any]) -> dict[str, Any]:
    """Build a single transaction dict with all common fields."""
    tx: dict[str, Any] = {
        "end_to_end_id": row["end_to_end_id"],
        "tx_id": row.get("tx_id", ""),
        "interbank_settlement_amount": row["interbank_settlement_amount"],
        "interbank_settlement_currency": row[
            "interbank_settlement_currency"
        ],
        "charge_bearer": row.get("charge_bearer", ""),
        "debtor_name": row.get("debtor_name", ""),
        "debtor_account_iban": row.get("debtor_account_iban", ""),
        "debtor_agent_bic": row.get("debtor_agent_bic", ""),
        "creditor_agent_bic": row.get("creditor_agent_bic", ""),
        "creditor_name": row.get("creditor_name", ""),
        "creditor_account_iban": row.get("creditor_account_iban", ""),
        "remittance_information": row.get("remittance_information", ""),
    }
    for key in _TX_COMMON:
        tx[key] = row.get(key, "")
    return tx


def _prepare_xml_data_v01(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.01 (root: pacs.008.001.01, BIC)."""
    hdr = _build_header(data)
    hdr["transactions"] = [
        _build_tx_base(row) for row in data
    ]
    # v01 uses single PrvsInstgAgt (unnumbered)
    for i, row in enumerate(data):
        hdr["transactions"][i]["prvs_instg_agt_bic"] = row.get(
            "prvs_instg_agt_bic", ""
        )
    return hdr


def _prepare_xml_data_v02_to_v04(
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.02-04 (FIToFICstmrCdtTrf, BIC/BICFI)."""
    hdr = _build_header(data)
    hdr["transactions"] = [
        _build_tx_base(row) for row in data
    ]
    for i, row in enumerate(data):
        hdr["transactions"][i]["clr_sys_ref"] = row.get("clr_sys_ref", "")
        hdr["transactions"][i]["prvs_instg_agt_bic"] = row.get(
            "prvs_instg_agt_bic", ""
        )
    return hdr


def _prepare_xml_data_v05_to_v06(
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.05-06 (BICFI, unnumbered PrvsInstgAgt)."""
    return _prepare_xml_data_v02_to_v04(data)


def _prepare_xml_data_v07(
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.07 (BICFI, numbered PrvsInstgAgt1/2/3)."""
    hdr = _build_header(data)
    hdr["transactions"] = [
        _build_tx_base(row) for row in data
    ]
    for i, row in enumerate(data):
        hdr["transactions"][i]["clr_sys_ref"] = row.get("clr_sys_ref", "")
        hdr["transactions"][i]["prvs_instg_agt1_bic"] = row.get(
            "prvs_instg_agt1_bic", ""
        )
        hdr["transactions"][i]["prvs_instg_agt2_bic"] = row.get(
            "prvs_instg_agt2_bic", ""
        )
        hdr["transactions"][i]["prvs_instg_agt3_bic"] = row.get(
            "prvs_instg_agt3_bic", ""
        )
    return hdr


def _prepare_xml_data_v08_to_v09(
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.08-09 (BICFI + UETR)."""
    hdr = _build_header(data)
    hdr["transactions"] = [
        _build_tx_base(row) for row in data
    ]
    for i, row in enumerate(data):
        hdr["transactions"][i]["clr_sys_ref"] = row.get("clr_sys_ref", "")
        hdr["transactions"][i]["uetr"] = row.get("uetr", "")
        # v08+ uses numbered PrvsInstgAgt1/2/3
        hdr["transactions"][i]["prvs_instg_agt1_bic"] = row.get(
            "prvs_instg_agt1_bic", ""
        )
        hdr["transactions"][i]["prvs_instg_agt2_bic"] = row.get(
            "prvs_instg_agt2_bic", ""
        )
        hdr["transactions"][i]["prvs_instg_agt3_bic"] = row.get(
            "prvs_instg_agt3_bic", ""
        )
    return hdr


def _prepare_xml_data_v10_to_v12(
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.10-12 (+ MndtRltdInf)."""
    base = _prepare_xml_data_v08_to_v09(data)
    for i, row in enumerate(data):
        base["transactions"][i]["mandate_id"] = row.get("mandate_id", "")
    return base


def _prepare_xml_data_v13(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare XML data for pacs.008.001.13 (+ XpryDtTm)."""
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
