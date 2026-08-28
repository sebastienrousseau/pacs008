# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What the CSV loaders do when the file is not the happy path.

Every branch here is one a user reaches by accident rather than by design: a
path that does not exist, a file that is not UTF-8, a directory where a file was
meant to be. They were the least-covered part of the package, which is the wrong
way round — the happy path is exercised constantly by everything downstream,
while these are reached only when somebody is already having a bad afternoon and
the message they get is all they have to go on.

Both loaders are covered, because they fail differently: `load_csv_data` reads
the file whole, `load_csv_data_streaming` yields chunks and so raises from inside
a generator, which nothing surfaces until the generator is consumed.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from pacs008.csv.load_csv_data import (
    load_csv_data,
    load_csv_data_streaming,
)
from pacs008.exceptions import DataSourceError


@pytest.fixture()
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A working directory the loaders will accept paths beneath."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_rows(path: Path, rows: list[dict[str, str]]) -> str:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["msg_id", "amount"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(path)


class TestMissingFile:
    """A path that does not resolve to a file."""

    def test_load_raises_file_not_found(self, workdir: Path) -> None:
        with pytest.raises((FileNotFoundError, DataSourceError, ValueError)):
            load_csv_data(str(workdir / "absent.csv"))

    def test_streaming_raises_when_consumed(self, workdir: Path) -> None:
        # The generator body does not run until something iterates it, so the
        # error surfaces at consumption rather than at the call. Asserting on
        # the bare call would pass while the failure was still ahead.
        stream = load_csv_data_streaming(str(workdir / "absent.csv"))
        with pytest.raises((FileNotFoundError, DataSourceError, ValueError)):
            list(stream)


class TestDirectoryInsteadOfFile:
    """A path that exists but is not a file."""

    def test_load_rejects_a_directory(self, workdir: Path) -> None:
        directory = workdir / "payments"
        directory.mkdir()
        with pytest.raises(
            (FileNotFoundError, IsADirectoryError, DataSourceError, ValueError)
        ):
            load_csv_data(str(directory))


class TestUndecodableFile:
    """Bytes that are not UTF-8.

    A CSV exported from a Windows tool in cp1252 hits this, which makes it one
    of the likelier failures in practice rather than a contrived one.
    """

    def test_load_raises_unicode_decode_error(self, workdir: Path) -> None:
        path = workdir / "latin1.csv"
        # 0xFF is not valid UTF-8 in any position.
        path.write_bytes(b"msg_id,amount\nMSG-001,\xff\xfe1000\n")
        with pytest.raises((UnicodeDecodeError, DataSourceError, ValueError)):
            load_csv_data(str(path))

    def test_streaming_raises_unicode_decode_error(
        self, workdir: Path
    ) -> None:
        path = workdir / "latin1-stream.csv"
        path.write_bytes(b"msg_id,amount\nMSG-001,\xff\xfe1000\n")
        with pytest.raises((UnicodeDecodeError, DataSourceError, ValueError)):
            list(load_csv_data_streaming(str(path)))


class TestEmptyFile:
    """A file with a header and no rows is not an error to read, but it is
    nothing to process, and saying so beats returning an empty list that the
    caller then treats as a successful run over zero payments."""

    def test_load_rejects_a_header_only_file(self, workdir: Path) -> None:
        path = _write_rows(workdir / "header-only.csv", [])
        with pytest.raises((DataSourceError, ValueError)):
            load_csv_data(path)

    def test_streaming_rejects_a_header_only_file(self, workdir: Path) -> None:
        path = _write_rows(workdir / "header-only-stream.csv", [])
        with pytest.raises((DataSourceError, ValueError)):
            list(load_csv_data_streaming(path))


class TestChunking:
    """The streaming loader's remainder branch.

    A file whose row count is not a multiple of the chunk size leaves rows in
    the buffer when the reader runs out, and those have to be yielded rather
    than dropped. Silently losing the tail of a payment file is the worst
    failure this module could have, and it would not raise.
    """

    def test_the_final_partial_chunk_is_yielded(self, workdir: Path) -> None:
        rows = [{"msg_id": f"MSG-{n:03d}", "amount": "1.00"} for n in range(7)]
        path = _write_rows(workdir / "seven.csv", rows)

        chunks = list(load_csv_data_streaming(path, chunk_size=3))

        assert [len(c) for c in chunks] == [3, 3, 1]
        seen = [row["msg_id"] for chunk in chunks for row in chunk]
        assert seen == [row["msg_id"] for row in rows]


# Windows has no geteuid and does not deny reads on a 000 file, and root reads
# regardless of mode on POSIX. Both are conditions where the branch cannot be
# reached, so the test is skipped rather than made to pass some other way.
_CANNOT_DENY_READS = (
    os.name == "nt" or getattr(os, "geteuid", lambda: 1)() == 0
)


@pytest.mark.skipif(
    _CANNOT_DENY_READS,
    reason="file modes do not deny reads for this user on this platform",
)
class TestUnreadableFile:
    """A file the process is not permitted to open.

    Reachable in practice: payment files arrive from another system, and a
    nightly job running as a different user than the one that wrote them is an
    ordinary way for this to happen. The loader has to surface it rather than
    return an empty result that reads as a run over zero payments.
    """

    def test_load_raises_rather_than_returning_nothing(
        self, workdir: Path
    ) -> None:
        path = workdir / "locked.csv"
        _write_rows(path, [{"msg_id": "MSG-001", "amount": "1.00"}])
        os.chmod(path, 0o000)
        try:
            with pytest.raises(
                (OSError, PermissionError, DataSourceError, ValueError)
            ):
                load_csv_data(str(path))
        finally:
            os.chmod(path, 0o600)

    def test_streaming_raises_when_consumed(self, workdir: Path) -> None:
        path = workdir / "locked-stream.csv"
        _write_rows(path, [{"msg_id": "MSG-001", "amount": "1.00"}])
        os.chmod(path, 0o000)
        try:
            with pytest.raises(
                (OSError, PermissionError, DataSourceError, ValueError)
            ):
                list(load_csv_data_streaming(str(path)))
        finally:
            os.chmod(path, 0o600)
