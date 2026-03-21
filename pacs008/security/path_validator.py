"""Path validation and sanitization to prevent security vulnerabilities."""

import os
import re
import tempfile
from pathlib import Path
from typing import Union


class PathValidationError(ValueError):
    """Raised when path validation fails."""


class SecurityError(PermissionError):
    """Raised when a security boundary is violated."""


def _is_allowed_directory(resolved_path: Path) -> bool:
    try:
        allowed_bases = [
            Path.cwd().resolve(),
            Path(tempfile.gettempdir()).resolve(),
            Path(os.path.join(os.path.sep, "var", "tmp")).resolve(),
        ]
        resolved_str = str(resolved_path)
        return any(
            resolved_str == str(base)
            or resolved_str.startswith(str(base) + os.sep)
            for base in allowed_bases
        )
    except Exception:
        return False


def _resolve_within_allowed_bases(
    untrusted_path: Union[str, Path],
    base_dir: Union[str, Path, None] = None,
) -> str:
    if not untrusted_path:
        raise PathValidationError("Path cannot be empty")
    path_str = str(untrusted_path)
    if ".." in path_str:
        raise PathValidationError("Path contains invalid traversal sequences")
    normalized_str = os.path.normpath(path_str)
    try:
        resolved_str = os.path.realpath(normalized_str)
    except (RuntimeError, OSError) as e:
        raise PathValidationError(f"Invalid path: {e}") from e
    if base_dir is not None:
        base_str = os.path.realpath(str(base_dir))
        allowed_bases = [base_str]
    else:
        allowed_bases = [
            os.path.realpath(os.getcwd()),
            os.path.realpath(tempfile.gettempdir()),
            os.path.realpath(os.path.join(os.path.sep, "var", "tmp")),
        ]
    for base in allowed_bases:
        if resolved_str == base or resolved_str.startswith(base + os.sep):
            return base + resolved_str[len(base):]
    if base_dir:
        raise SecurityError(
            f"Path '{resolved_str}' escapes base directory '{base_dir}'."
        )
    raise SecurityError(
        f"Path '{resolved_str}' is outside allowed directories."
    )


def validate_path(
    untrusted_path: Union[str, Path],
    must_exist: bool = False,
    base_dir: Union[str, Path, None] = None,
) -> str:
    safe_path = _resolve_within_allowed_bases(untrusted_path, base_dir)
    if must_exist and not os.path.exists(safe_path):
        raise FileNotFoundError(f"Path does not exist: {safe_path}")
    return safe_path


def sanitize_for_log(user_input: str, max_length: int = 100) -> str:
    if not user_input:
        return ""
    sanitized = re.sub(r"[\r\n\t\x00-\x1f\x7f-\x9f]", "", user_input)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized
