"""Tests for pacs008.constants module."""

from pacs008.constants import (
    APP_NAME,
    BASE_DIR,
    SCHEMAS_DIR,
    TEMPLATES_DIR,
    VERSION,
    valid_xml_types,
)


def test_valid_xml_types_has_20_entries():
    assert len(valid_xml_types) == 20


def test_valid_xml_types_format():
    for t in valid_xml_types:
        assert t.startswith("pacs.")


def test_app_name():
    assert APP_NAME == "Pacs008"


def test_version():
    assert VERSION == "0.0.1"


def test_base_dir_exists():
    assert BASE_DIR.exists()


def test_schemas_dir():
    assert SCHEMAS_DIR == BASE_DIR / "schemas"


def test_templates_dir():
    assert TEMPLATES_DIR == BASE_DIR / "templates"
