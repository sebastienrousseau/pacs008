# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pydantic models for FastAPI request/response validation."""

# pylint: disable=too-few-public-methods

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class DataSourceType(str, Enum):
    """Supported data source types."""

    CSV = "csv"
    SQLITE = "sqlite"
    JSON = "json"
    JSONL = "jsonl"
    PARQUET = "parquet"


class MessageType(str, Enum):
    """Supported ISO 20022 pacs message types."""

    PACS_002_12 = "pacs.002.001.12"
    PACS_003_09 = "pacs.003.001.09"
    PACS_004_11 = "pacs.004.001.11"
    PACS_007_11 = "pacs.007.001.11"
    PACS_008_01 = "pacs.008.001.01"
    PACS_008_02 = "pacs.008.001.02"
    PACS_008_03 = "pacs.008.001.03"
    PACS_008_04 = "pacs.008.001.04"
    PACS_008_05 = "pacs.008.001.05"
    PACS_008_06 = "pacs.008.001.06"
    PACS_008_07 = "pacs.008.001.07"
    PACS_008_08 = "pacs.008.001.08"
    PACS_008_09 = "pacs.008.001.09"
    PACS_008_10 = "pacs.008.001.10"
    PACS_008_11 = "pacs.008.001.11"
    PACS_008_12 = "pacs.008.001.12"
    PACS_008_13 = "pacs.008.001.13"
    PACS_009_10 = "pacs.009.001.10"
    PACS_010_05 = "pacs.010.001.05"
    PACS_028_05 = "pacs.028.001.05"


class ValidationRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request model for data validation."""

    data_source: DataSourceType = Field(
        ..., description="Type of data source (csv, sqlite, json, etc.)"
    )
    file_path: str = Field(..., description="Path to the data file")
    message_type: MessageType = Field(
        default=MessageType.PACS_008_01,
        description="ISO 20022 pacs.008 message type",
    )
    table_name: Optional[str] = Field(
        default=None,
        description="Table name for SQLite sources",
    )

    class Config:
        """Pydantic config."""

        use_enum_values = False


class GenerateXMLRequest(BaseModel):
    """Request model for XML generation."""

    data_source: DataSourceType = Field(..., description="Type of data source")
    file_path: str = Field(..., description="Path to the data file")
    message_type: MessageType = Field(
        default=MessageType.PACS_008_01,
        description="ISO 20022 pacs.008 message type",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory for generated XML",
    )
    validate_only: bool = Field(
        default=False,
        description="Only validate, don't generate XML",
    )
    table_name: Optional[str] = Field(
        default=None,
        description="Table name for SQLite sources",
    )

    class Config:
        """Pydantic config."""

        use_enum_values = False


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Field name or JSON path")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="The invalid value")


class ValidationResponse(BaseModel):
    """Response model for validation results."""

    is_valid: bool = Field(..., description="Whether data is valid")
    total_rows: int = Field(..., description="Total number of rows")
    valid_rows: int = Field(default=0, description="Number of valid rows")
    invalid_rows: int = Field(default=0, description="Number of invalid rows")
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors",
    )

    @field_validator("invalid_rows", mode="after")
    @classmethod
    def calculate_invalid_rows(cls, v: int, info: ValidationInfo) -> int:
        """Calculate invalid rows from total and valid counts.

        Args:
            v: Current invalid_rows value.
            info: Validation info containing all field values.

        Returns:
            Calculated invalid rows (total - valid).
        """
        # Pydantic v2 uses info.data instead of values dict
        if hasattr(info, "data"):
            data = info.data
            if "total_rows" in data and "valid_rows" in data:
                total = int(data["total_rows"])
                valid = int(data["valid_rows"])
                return total - valid
        return v  # pragma: no cover


class GenerateXMLResponse(BaseModel):
    """Response model for XML generation."""

    success: bool = Field(..., description="Whether generation succeeded")
    message: str = Field(..., description="Result message")
    file_path: Optional[str] = Field(None, description="Path to generated XML")
    validation_errors: list[ValidationError] = Field(
        default_factory=list,
        description="Validation errors if validation failed",
    )


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Current job status (pending, processing, success, failed, cancelled)",
    )
    message: str = Field(..., description="Status message")
    result: Optional[GenerateXMLResponse] = Field(
        None, description="Result when status is success"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    progress_percent: int = Field(
        default=0, description="Progress percentage (0-100)"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = True


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    message: str = Field(..., description="Health check message")
