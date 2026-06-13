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

"""PII redaction and log-injection sanitisation.

Used by ``log_event`` to scrub sensitive fields (IBAN, BIC, name,
account) before they reach log aggregation systems. This is the
GDPR/PCI-DSS compliance hinge — anything that *might* contain PII should
flow through ``_redact_pii_from_dict`` first.
"""

from typing import Any


def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data for logging.

    Args:
        value: The sensitive value to mask.
        visible_chars: Number of characters to show at start and end.

    Returns:
        Masked string showing only first and last ``visible_chars``.

    Examples:
        >>> mask_sensitive_data("GB29NWBK60161331926819", 4)
        'GB29**************6819'
        >>> mask_sensitive_data("Short", 4)
        '****'
    """
    if len(value) <= visible_chars * 2:
        return "****"
    masked_length = len(value) - (visible_chars * 2)
    return (
        f"{value[:visible_chars]}{'*' * masked_length}{value[-visible_chars:]}"
    )


def _sanitize_value(value: Any) -> Any:
    """Strip newlines and carriage returns to prevent log injection (CWE-117)."""
    if isinstance(value, str):
        return value.replace("\n", "").replace("\r", "")
    return value


def _redact_pii_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Redact PII from dictionary fields recursively.

    Implements GDPR/PCI-DSS compliant logging by masking sensitive fields
    before they reach log aggregation systems. All string values are also
    sanitised against log injection (CWE-117).

    Redacted fields (by case-insensitive substring match):

    - ``*iban*`` — first 4 + last 4 characters
    - ``*bic*`` — first 4 + last 2 characters
    - ``*name*`` — replaced with ``[REDACTED]``
    - ``*account*`` — first 4 + last 4 characters

    Args:
        data: Dictionary that may contain PII fields.

    Returns:
        New dictionary with PII fields redacted and strings sanitised.
    """
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()

        if isinstance(value, dict):
            redacted[key] = _redact_pii_from_dict(value)
        elif isinstance(value, list):
            redacted[key] = [
                (
                    _redact_pii_from_dict(item)
                    if isinstance(item, dict)
                    else _sanitize_value(item)
                )
                for item in value
            ]
        elif "iban" in key_lower and isinstance(value, str):
            redacted[key] = mask_sensitive_data(
                _sanitize_value(value), visible_chars=4
            )
        elif "bic" in key_lower and isinstance(value, str):
            val = _sanitize_value(value)
            redacted[key] = (
                f"{val[:4]}**{val[-2:]}" if len(val) > 6 else "****"
            )
        elif "name" in key_lower and isinstance(value, str):
            redacted[key] = "[REDACTED]"
        elif "account" in key_lower and isinstance(value, str):
            redacted[key] = mask_sensitive_data(
                _sanitize_value(value), visible_chars=4
            )
        else:
            redacted[key] = _sanitize_value(value)

    return redacted
