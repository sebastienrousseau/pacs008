"""End-to-end gold master pipeline tests.

Automates the flow: Source File -> Library Ingestion -> XML Output -> XSD Validation.

Tests discover sample files in tests/gold_master/ and ensure the library can
convert each into valid pacs.008 XML without manual mapping. Each gold master
file is named with a version prefix (e.g., v01_basic.json, v08_uetr.json).
"""

import json
import os
from pathlib import Path

import pytest

from pacs008.constants import TEMPLATES_DIR, valid_xml_types
from pacs008.csv.load_csv_data import load_csv_data
from pacs008.xml.generate_xml import generate_xml_string

GOLD_MASTER_DIR = Path(__file__).parent / "gold_master"

# Map gold master file prefixes to pacs.008 versions
VERSION_MAP = {
    "v01": "pacs.008.001.01",
    "v02": "pacs.008.001.02",
    "v03": "pacs.008.001.03",
    "v04": "pacs.008.001.04",
    "v05": "pacs.008.001.05",
    "v06": "pacs.008.001.06",
    "v07": "pacs.008.001.07",
    "v08": "pacs.008.001.08",
    "v09": "pacs.008.001.09",
    "v10": "pacs.008.001.10",
    "v11": "pacs.008.001.11",
    "v12": "pacs.008.001.12",
    "v13": "pacs.008.001.13",
}


def _discover_gold_master_files():
    """Discover all gold master data files."""
    if not GOLD_MASTER_DIR.exists():
        return []
    files = []
    for f in sorted(GOLD_MASTER_DIR.iterdir()):
        if f.suffix in (".json", ".csv") and f.stem != "__init__":
            files.append(f)
    return files


def _version_from_filename(filename: str) -> str:
    """Extract version from filename prefix (e.g., 'v01_basic' -> 'pacs.008.001.01')."""
    prefix = filename.split("_")[0]
    version = VERSION_MAP.get(prefix)
    if not version:
        raise ValueError(
            f"Cannot determine version from filename: {filename}. "
            f"Expected prefix like v01, v05, etc."
        )
    return version


def _load_data(filepath: Path) -> list[dict]:
    """Load data from JSON or CSV file."""
    if filepath.suffix == ".json":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    elif filepath.suffix == ".csv":
        return load_csv_data(str(filepath))
    else:
        raise ValueError(f"Unsupported gold master file type: {filepath.suffix}")


def _template_path(version: str) -> str:
    return str(TEMPLATES_DIR / version / "template.xml")


def _xsd_path(version: str) -> str:
    return str(TEMPLATES_DIR / version / f"{version}.xsd")


# Discover files for parametrization
_gold_master_files = _discover_gold_master_files()


@pytest.mark.integration
class TestGoldMasterPipeline:
    """End-to-end: Source File -> Ingestion -> XML -> XSD Validation."""

    @pytest.mark.parametrize(
        "filepath",
        _gold_master_files,
        ids=[f.stem for f in _gold_master_files],
    )
    def test_gold_master_produces_valid_xml(self, filepath):
        """Each gold master file must produce XSD-valid XML."""
        version = _version_from_filename(filepath.stem)

        # Step 1: Load data from file
        data = _load_data(filepath)
        assert len(data) > 0, f"Gold master file is empty: {filepath}"

        # Step 2: Generate XML string (includes XSD validation internally)
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )

        # Step 3: Verify XML structure
        assert xml.strip(), "Generated XML is empty"
        assert f"urn:iso:std:iso:20022:tech:xsd:{version}" in xml

    @pytest.mark.parametrize(
        "filepath",
        [f for f in _gold_master_files if f.suffix == ".json"],
        ids=[f.stem for f in _gold_master_files if f.suffix == ".json"],
    )
    def test_gold_master_json_roundtrip(self, filepath):
        """JSON gold master data must survive the full pipeline."""
        version = _version_from_filename(filepath.stem)
        data = _load_data(filepath)

        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )

        # Verify key data fields appear in output XML
        for row in data:
            assert row["end_to_end_id"] in xml
            if row.get("debtor_name"):
                assert row["debtor_name"] in xml

    @pytest.mark.parametrize(
        "filepath",
        [f for f in _gold_master_files if f.suffix == ".csv"],
        ids=[f.stem for f in _gold_master_files if f.suffix == ".csv"],
    )
    def test_gold_master_csv_ingestion(self, filepath):
        """CSV gold master files must load and generate valid XML."""
        version = _version_from_filename(filepath.stem)
        data = _load_data(filepath)
        assert len(data) > 0

        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "<MsgId>" in xml


@pytest.mark.integration
class TestGoldMasterCoverage:
    """Verify gold master files exist for key version groups."""

    def test_has_v01_sample(self):
        assert any(
            f.stem.startswith("v01") for f in _gold_master_files
        ), "Missing v01 gold master file"

    def test_has_bicfi_sample(self):
        assert any(
            f.stem.startswith("v05") for f in _gold_master_files
        ), "Missing v05 (BICFI) gold master file"

    def test_has_uetr_sample(self):
        assert any(
            f.stem.startswith("v08") for f in _gold_master_files
        ), "Missing v08 (UETR) gold master file"

    def test_has_mandate_sample(self):
        assert any(
            f.stem.startswith("v10") for f in _gold_master_files
        ), "Missing v10 (mandate) gold master file"

    def test_has_v13_sample(self):
        assert any(
            f.stem.startswith("v13") for f in _gold_master_files
        ), "Missing v13 (full) gold master file"

    def test_has_csv_sample(self):
        assert any(
            f.suffix == ".csv" for f in _gold_master_files
        ), "Missing CSV gold master file"

    def test_has_json_sample(self):
        assert any(
            f.suffix == ".json" for f in _gold_master_files
        ), "Missing JSON gold master file"

    def test_has_v02_sample(self):
        assert any(
            f.stem.startswith("v02") for f in _gold_master_files
        ), "Missing v02 gold master file"

    def test_has_v03_sample(self):
        assert any(
            f.stem.startswith("v03") for f in _gold_master_files
        ), "Missing v03 (BICFI transition) gold master file"

    def test_has_v04_sample(self):
        assert any(
            f.stem.startswith("v04") for f in _gold_master_files
        ), "Missing v04 gold master file"

    def test_has_v06_sample(self):
        assert any(
            f.stem.startswith("v06") for f in _gold_master_files
        ), "Missing v06 gold master file"

    def test_has_v07_sample(self):
        assert any(
            f.stem.startswith("v07") for f in _gold_master_files
        ), "Missing v07 gold master file"

    def test_has_v09_sample(self):
        assert any(
            f.stem.startswith("v09") for f in _gold_master_files
        ), "Missing v09 (UETR) gold master file"

    def test_has_v11_sample(self):
        assert any(
            f.stem.startswith("v11") for f in _gold_master_files
        ), "Missing v11 (mandate) gold master file"

    def test_has_v12_sample(self):
        assert any(
            f.stem.startswith("v12") for f in _gold_master_files
        ), "Missing v12 (mandate) gold master file"

    def test_all_13_versions_covered(self):
        """Every version v01-v13 must have at least one gold master file."""
        for v in range(1, 14):
            prefix = f"v{v:02d}"
            assert any(
                f.stem.startswith(prefix) for f in _gold_master_files
            ), f"Missing gold master file for {prefix}"


@pytest.mark.integration
class TestGoldMasterCompliance:
    """Gold master data with SWIFT compliance cleansing."""

    @pytest.mark.parametrize(
        "filepath",
        _gold_master_files,
        ids=[f.stem for f in _gold_master_files],
    )
    def test_gold_master_data_is_swift_compliant(self, filepath):
        """Gold master data should already be SWIFT-compliant."""
        from pacs008.compliance.swift_charset import (
            cleanse_data_with_report,
        )

        data = _load_data(filepath)
        _, report = cleanse_data_with_report(data)
        assert report.is_clean, (
            f"{filepath.name} has SWIFT compliance violations: "
            f"{report.violation_count} violations"
        )

    @pytest.mark.parametrize(
        "filepath",
        [f for f in _gold_master_files if f.suffix == ".json"],
        ids=[f.stem for f in _gold_master_files if f.suffix == ".json"],
    )
    def test_gold_master_roundtrip_preserves_amounts(self, filepath):
        """Amount values must survive the full pipeline unchanged."""
        data = _load_data(filepath)
        version = _version_from_filename(filepath.stem)
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        for row in data:
            assert row["interbank_settlement_amount"] in xml

    @pytest.mark.parametrize(
        "filepath",
        [f for f in _gold_master_files if f.suffix == ".json"],
        ids=[f.stem for f in _gold_master_files if f.suffix == ".json"],
    )
    def test_gold_master_settlement_method_preserved(self, filepath):
        """Settlement method must appear in XML output."""
        data = _load_data(filepath)
        version = _version_from_filename(filepath.stem)
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert f"<SttlmMtd>{data[0]['settlement_method']}</SttlmMtd>" in xml
