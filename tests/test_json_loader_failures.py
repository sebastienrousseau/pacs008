# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What the JSON and JSONL loaders do with input that is not what they wanted.

Four loaders share one shape -- read, parse, complain usefully -- and the
complaining half was the uncovered half. JSONL is the interesting case: a file
is a sequence of independent documents, so one malformed line among thousands is
the realistic failure, and the loader has to say which line rather than that the
file was bad.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pacs008.exceptions import DataSourceError
from pacs008.json.load_json_data import (
    load_json_data,
    load_jsonl_data,
    load_jsonl_data_streaming,
)


@pytest.fixture(autouse=True)
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestMissingFiles:
    def test_json_missing(self, workdir: Path) -> None:
        with pytest.raises((FileNotFoundError, DataSourceError, ValueError)):
            load_json_data(str(workdir / "absent.json"))

    def test_jsonl_missing(self, workdir: Path) -> None:
        with pytest.raises((FileNotFoundError, DataSourceError, ValueError)):
            load_jsonl_data(str(workdir / "absent.jsonl"))

    def test_jsonl_streaming_missing(self, workdir: Path) -> None:
        with pytest.raises((FileNotFoundError, DataSourceError, ValueError)):
            list(load_jsonl_data_streaming(str(workdir / "absent.jsonl")))


class TestMalformedJson:
    def test_broken_syntax_is_reported_as_a_data_source_error(
        self, workdir: Path
    ) -> None:
        path = workdir / "broken.json"
        path.write_text('{"msg_id": "MSG-001",', encoding="utf-8")
        with pytest.raises((DataSourceError, ValueError)):
            load_json_data(str(path))

    def test_a_bare_list_of_scalars_is_refused(self, workdir: Path) -> None:
        # A JSON array is accepted, but every element has to be an object: a
        # list of strings would otherwise reach the generator as rows with no
        # fields and fail much further downstream.
        path = workdir / "scalars.json"
        path.write_text('["MSG-001", "MSG-002"]', encoding="utf-8")
        with pytest.raises((DataSourceError, ValueError, TypeError)):
            load_json_data(str(path))

    def test_a_single_object_is_wrapped_in_a_list(self, workdir: Path) -> None:
        path = workdir / "one.json"
        path.write_text('{"msg_id": "MSG-001"}', encoding="utf-8")
        assert load_json_data(str(path)) == [{"msg_id": "MSG-001"}]


class TestMalformedJsonl:
    def test_one_bad_line_fails_the_read(self, workdir: Path) -> None:
        path = workdir / "one-bad-line.jsonl"
        path.write_text(
            '{"msg_id": "MSG-001"}\n'
            "not json at all\n"
            '{"msg_id": "MSG-003"}\n',
            encoding="utf-8",
        )
        with pytest.raises((DataSourceError, ValueError)):
            load_jsonl_data(str(path))

    def test_streaming_fails_on_the_bad_line_too(self, workdir: Path) -> None:
        path = workdir / "one-bad-line-stream.jsonl"
        path.write_text(
            '{"msg_id": "MSG-001"}\n' "not json at all\n",
            encoding="utf-8",
        )
        with pytest.raises((DataSourceError, ValueError)):
            list(load_jsonl_data_streaming(str(path)))

    def test_blank_lines_are_tolerated(self, workdir: Path) -> None:
        # A trailing newline is how every text editor ends a file, so treating
        # the resulting empty line as a parse error would reject almost every
        # hand-made fixture.
        path = workdir / "blank-lines.jsonl"
        path.write_text(
            '{"msg_id": "MSG-001"}\n\n{"msg_id": "MSG-002"}\n\n',
            encoding="utf-8",
        )
        rows = load_jsonl_data(str(path))
        assert [row["msg_id"] for row in rows] == ["MSG-001", "MSG-002"]
