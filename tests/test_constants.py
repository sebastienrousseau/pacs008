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
    """`constants.VERSION` must equal the package version.

    Deliberately not a literal. This test asserted `== "0.0.1"` and passed
    for nine releases while `constants.VERSION` really was `0.0.1` and
    `pyproject.toml` had reached `0.0.10` — the pinned literal was not
    guarding the value, it was preserving a stale one. Anything reading
    `constants.VERSION` reported `0.0.1` the entire time.
    """
    import pacs008

    assert VERSION == pacs008.__version__


def test_base_dir_exists():
    assert BASE_DIR.exists()


def test_schemas_dir():
    assert SCHEMAS_DIR == BASE_DIR / "schemas"


def test_templates_dir():
    assert TEMPLATES_DIR == BASE_DIR / "templates"
