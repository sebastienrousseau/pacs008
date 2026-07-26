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

"""Regression tests for the PEP 561 ``py.typed`` marker.

``pacs008`` is ``mypy --strict`` clean internally, but without the
``py.typed`` marker shipped in the distribution, downstream consumers get
none of those annotations. If the marker is ever dropped from the source
tree or the packaging ``include`` list, these tests fail before a release
goes out.
"""

import importlib.util
import os


def _package_dir() -> str:
    """Return the installed ``pacs008`` package directory."""
    spec = importlib.util.find_spec("pacs008")
    assert spec is not None and spec.origin is not None
    return os.path.dirname(spec.origin)


def test_py_typed_marker_present() -> None:
    """The ``py.typed`` marker must sit beside the package ``__init__``."""
    marker = os.path.join(_package_dir(), "py.typed")
    assert os.path.isfile(marker), (
        "pacs008 declares itself typed (mypy --strict) but the PEP 561 "
        "py.typed marker is missing — downstream consumers would not see "
        "the annotations. Restore pacs008/py.typed and its packaging "
        "include entry."
    )


def test_py_typed_marker_is_empty() -> None:
    """PEP 561 marks a package as typed with an empty ``py.typed`` file."""
    marker = os.path.join(_package_dir(), "py.typed")
    assert os.path.getsize(marker) == 0
