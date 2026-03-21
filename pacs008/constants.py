"""Shared constants and configuration for the pacs008 library."""

import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).resolve()

VERSION = "0.0.1"
SCHEMAS_DIR = BASE_DIR / "schemas"
TEMPLATES_DIR = BASE_DIR / "templates"

valid_xml_types = [
    "pacs.008.001.01",
    "pacs.008.001.02",
    "pacs.008.001.03",
    "pacs.008.001.04",
    "pacs.008.001.05",
    "pacs.008.001.06",
    "pacs.008.001.07",
    "pacs.008.001.08",
    "pacs.008.001.09",
    "pacs.008.001.10",
    "pacs.008.001.11",
    "pacs.008.001.12",
    "pacs.008.001.13",
]

APP_NAME = "Pacs008"
APP_DESCRIPTION = """
A powerful Python library that enables you to create
ISO 20022 pacs.008 FI-to-FI Customer Credit Transfer
XML messages from CSV or SQLite data files.\n
https://pacs008.com
"""

__all__ = [
    "APP_DESCRIPTION",
    "APP_NAME",
    "BASE_DIR",
    "SCHEMAS_DIR",
    "TEMPLATES_DIR",
    "VERSION",
    "valid_xml_types",
]
