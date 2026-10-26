"""Shared fixtures for the test suite."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from pacs008.constants import TEMPLATES_DIR


@pytest.fixture
def template_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], tuple[str, str]]:
    """Copy one version's templates into tmp_path and work from there.

    Generation writes ``<version>.xml`` next to the template it is given,
    so a test that passes the packaged template overwrites the shipped
    sample. The copy keeps the ``pacs008/templates/<version>`` layout the
    API resolves against the working directory, and the working directory
    moves to tmp_path because generation only writes beneath it.

    Returns a function taking a message version and returning the paths
    of the copied ``template.xml`` and XSD.
    """

    def copy(version: str) -> tuple[str, str]:
        dest = tmp_path / "pacs008" / "templates" / version
        shutil.copytree(TEMPLATES_DIR / version, dest)
        monkeypatch.chdir(tmp_path)
        return str(dest / "template.xml"), str(dest / f"{version}.xsd")

    return copy
