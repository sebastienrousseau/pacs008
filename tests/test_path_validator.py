"""Tests for path validation and sanitization security module."""

import os
import tempfile

import pytest

from pacs008.security.path_validator import (
    PathValidationError,
    SecurityError,
    _is_allowed_directory,
    sanitize_for_log,
    validate_path,
)


class TestValidatePath:
    """Test path validation against traversal attacks."""

    def test_valid_path_in_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        result = validate_path(str(test_file), must_exist=True)
        assert result == str(test_file)

    def test_valid_path_must_exist_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = validate_path(str(tmp_path / "nonexistent.txt"), must_exist=False)
        assert "nonexistent.txt" in result

    def test_must_exist_raises_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            validate_path(str(tmp_path / "missing.txt"), must_exist=True)

    def test_empty_path_raises(self):
        with pytest.raises(PathValidationError, match="empty"):
            validate_path("")

    def test_traversal_attack_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PathValidationError, match="traversal"):
            validate_path("../../etc/passwd")

    def test_base_dir_constraint(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "sub"
        sub.mkdir()
        test_file = sub / "file.txt"
        test_file.write_text("data")
        result = validate_path(str(test_file), base_dir=str(tmp_path))
        assert "file.txt" in result

    def test_base_dir_escape_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises((SecurityError, PathValidationError)):
            validate_path("/etc/passwd", base_dir=str(tmp_path))

    def test_temp_dir_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        tmp_file = os.path.join(tempfile.gettempdir(), "test_pacs008.txt")
        # Don't require existence, just validate path is allowed
        result = validate_path(tmp_file, must_exist=False)
        assert "test_pacs008.txt" in result


class TestSanitizeForLog:
    """Test log sanitization (CWE-117 prevention)."""

    def test_removes_newlines(self):
        assert sanitize_for_log("hello\nworld") == "helloworld"

    def test_removes_carriage_return(self):
        assert sanitize_for_log("hello\rworld") == "helloworld"

    def test_removes_tabs(self):
        assert sanitize_for_log("hello\tworld") == "helloworld"

    def test_removes_control_chars(self):
        assert sanitize_for_log("hello\x00world") == "helloworld"

    def test_truncates_long_input(self):
        long_input = "a" * 200
        result = sanitize_for_log(long_input, max_length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_empty_input(self):
        assert sanitize_for_log("") == ""

    def test_clean_input_unchanged(self):
        assert sanitize_for_log("clean text") == "clean text"

    def test_custom_max_length(self):
        result = sanitize_for_log("abcdefghij", max_length=5)
        assert result == "abcde..."


class TestIsAllowedDirectory:
    """Test internal allowed directory check."""

    def test_cwd_allowed(self):
        from pathlib import Path
        assert _is_allowed_directory(Path.cwd().resolve())

    def test_tmp_allowed(self):
        from pathlib import Path
        assert _is_allowed_directory(Path(tempfile.gettempdir()).resolve())

    def test_root_not_allowed(self):
        from pathlib import Path
        assert not _is_allowed_directory(Path("/usr/bin").resolve())
