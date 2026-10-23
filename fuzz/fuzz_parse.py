# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Coverage-guided fuzzing of ``pacs008.xml.parser.parse`` with Atheris.

``parse`` is the inbound entry point: it takes XML from outside the
institution. Its contract is that any input either classifies into a
consistent :class:`ParsedMessage` or raises :class:`ParseError`. Any
other exception, or a result that contradicts itself, is a crash that
libFuzzer reports and minimises.

An input whose first byte is ``0x00`` is passed as text (the rest,
decoded as UTF-8), so both the ``str`` and the ``bytes`` paths are
exercised. Every other input is passed as bytes as it stands, so the
files in ``fuzz/corpus/`` (real-shaped messages and the inputs of fixed
bugs) are seeds and regression cases at once.

Run (Linux x86_64, Python 3.12 to 3.14)::

    pip install --require-hashes -r .github/requirements/poetry.txt
    poetry install --only main
    poetry run pip install --require-hashes -r .github/requirements/fuzz.txt
    poetry run python fuzz/fuzz_parse.py fuzz/corpus -max_total_time=60
"""

import sys

import atheris

with atheris.instrument_imports():
    from pacs008.xml.parser import ParseError, parse


def _payload(data: bytes) -> str | bytes:
    """The argument this input hands to ``parse``."""
    if data[:1] == b"\x00":
        return data[1:].decode("utf-8", "replace")
    return data


def test_one_input(data: bytes) -> None:
    """Parse one input and hold the result to the contract."""
    try:
        msg = parse(_payload(data))
    except ParseError:
        return
    if msg.msg_def_idr != f"{msg.msg_family}.{msg.version}":
        raise AssertionError(f"inconsistent classification: {msg!r}")
    if msg.envelope_wrapped != (msg.bah is not None):
        raise AssertionError(f"envelope flag disagrees with BAH: {msg!r}")


def main() -> None:
    """Hand the harness to libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
