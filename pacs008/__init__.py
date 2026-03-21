"""The Python pacs008 module."""

__version__ = "0.0.1"

from pacs008.__main__ import main
from pacs008.core.core import process_files
from pacs008.exceptions import DataSourceError, PaymentValidationError
from pacs008.xml.generate_xml import generate_xml_string

__all__ = [
    "main",
    "process_files",
    "generate_xml_string",
    "PaymentValidationError",
    "DataSourceError",
    "__version__",
]
