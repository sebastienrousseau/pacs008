"""Guard the package version against the files that restate it.

`__version__`, `pyproject.toml`, `SECURITY.md` and `CHANGELOG.md` each
carry the version independently, and nothing tied them together. That is
how `0.0.8` reached PyPI with `cryptography<50.0.0` after the tree had
already been changed to `<51.0.0`: the constraint moved, the version did
not, and no release was cut — so every dependent kept resolving against
the old metadata and could not install the patched `cryptography` at
all.

These tests fail loudly when the four disagree.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import tomllib

import pacs008

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
SECURITY = ROOT / "SECURITY.md"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def _pyproject_version() -> str:
    with PYPROJECT.open("rb") as handle:
        return str(tomllib.load(handle)["tool"]["poetry"]["version"])


def _changelog_versions() -> list[str]:
    return HEADING.findall(CHANGELOG.read_text(encoding="utf-8"))


def test_dunder_version_is_semver() -> None:
    assert SEMVER.match(
        pacs008.__version__
    ), f"__version__ is {pacs008.__version__!r}, which is not X.Y.Z"


def test_dunder_version_matches_pyproject() -> None:
    assert pacs008.__version__ == _pyproject_version(), (
        f"pacs008.__version__ is {pacs008.__version__!r} but "
        f"pyproject.toml says {_pyproject_version()!r}"
    )


def test_changelog_documents_the_current_version() -> None:
    versions = _changelog_versions()
    assert versions, "CHANGELOG.md has no '## [X.Y.Z]' headings"
    assert pacs008.__version__ in versions, (
        f"CHANGELOG.md has no entry for {pacs008.__version__}; "
        f"newest documented is {versions[0]}"
    )


def test_changelog_newest_entry_is_the_current_version() -> None:
    versions = _changelog_versions()
    assert versions[0] == pacs008.__version__, (
        f"the newest CHANGELOG entry is {versions[0]} but the package is "
        f"{pacs008.__version__} — a release was cut without a changelog "
        f"entry, or an entry was added without bumping the version"
    )


def test_changelog_entries_are_ordered_newest_first() -> None:
    versions = _changelog_versions()
    keyed = [tuple(int(p) for p in v.split(".")) for v in versions]
    assert keyed == sorted(
        keyed, reverse=True
    ), f"CHANGELOG.md entries are out of order: {versions}"


def test_changelog_has_no_duplicate_versions() -> None:
    versions = _changelog_versions()
    duplicates = {v for v in versions if versions.count(v) > 1}
    assert (
        not duplicates
    ), f"CHANGELOG.md documents {duplicates} more than once"


def test_security_policy_names_the_current_version() -> None:
    text = SECURITY.read_text(encoding="utf-8")
    assert f"`{pacs008.__version__}`" in text, (
        f"SECURITY.md does not mention {pacs008.__version__}; its "
        f"supported-versions table is stale"
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="importlib.metadata shape differs"
)
def test_installed_metadata_matches_the_source() -> None:
    """The built distribution must agree with the source tree.

    An editable install reads `pyproject.toml`, so a mismatch here means
    the package was built from a different version than is checked out.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("pacs008")
    except PackageNotFoundError:  # pragma: no cover - not installed
        pytest.skip("pacs008 is not installed in this environment")

    assert installed == pacs008.__version__, (
        f"installed distribution is {installed} but the source tree is "
        f"{pacs008.__version__}"
    )


def test_cryptography_constraint_admits_the_patched_release() -> None:
    """The advisory floor must be resolvable by dependents.

    `0.0.8` shipped `cryptography<50.0.0`, which made the patched
    `cryptography 50.0.0` unresolvable for anything depending on this
    package. Dependents saw `ResolutionImpossible`, not a warning.
    """
    from packaging.requirements import Requirement
    from packaging.version import Version

    with PYPROJECT.open("rb") as handle:
        deps = tomllib.load(handle)["tool"]["poetry"]["dependencies"]

    raw = deps["cryptography"]
    spec = raw if isinstance(raw, str) else raw["version"]
    # Poetry's caret/tilde forms are not PEP 440; this project uses plain
    # comparators, so the string is usable as-is.
    requirement = Requirement(f"cryptography{spec}")

    assert requirement.specifier.contains(Version("50.0.0")), (
        f"cryptography{spec} excludes 50.0.0, the release that patches "
        f"the advisory — every dependent of this package would be unable "
        f"to install it"
    )
