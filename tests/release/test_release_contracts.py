from __future__ import annotations

import importlib.util
from email.message import Message
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI job
    import tomli as tomllib

ROOT = Path(__file__).parents[2]
EXPECTED_PYTHONS = [f"3.{minor}" for minor in range(10, 15)]
EXPECTED_SPECIFIER = SpecifierSet(">=3.10,<3.15")

_SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "check_distribution", ROOT / "scripts/check_distribution.py"
)
assert _SCRIPT_SPEC is not None and _SCRIPT_SPEC.loader is not None
_SCRIPT_MODULE = importlib.util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(_SCRIPT_MODULE)
_requires_python_failures = _SCRIPT_MODULE._requires_python_failures
_sdist_license_failures = _SCRIPT_MODULE._sdist_license_failures
_source_license_failures = _SCRIPT_MODULE._source_license_failures
_wheel_license_failures = _SCRIPT_MODULE._wheel_license_failures


def _metadata(requires_python: str | None) -> Message:
    metadata = Message()
    if requires_python is not None:
        metadata["Requires-Python"] = requires_python
    return metadata


def _pyproject(tmp_path: Path, requires_python: str) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        f'[project]\nname = "example"\nversion = "1.0.0"\n'
        f'requires-python = "{requires_python}"\n',
        encoding="utf-8",
    )
    return path


def _license_metadata(
    tmp_path: Path,
    *,
    expression: str = "MIT",
    license_files: str = '["LICENSE"]',
    classifier: str = "",
) -> Path:
    path = tmp_path / "pyproject.toml"
    classifiers = f'\nclassifiers = ["{classifier}"]' if classifier else ""
    path.write_text(
        f'[project]\nlicense = "{expression}"\nlicense-files = {license_files}{classifiers}\n',
        encoding="utf-8",
    )
    return path


def test_requires_python_validation_accepts_semantically_equivalent_order(
    tmp_path: Path,
) -> None:
    metadata = _metadata("<3.15,>=3.10")

    assert _requires_python_failures(metadata, _pyproject(tmp_path, ">=3.10,<3.15")) == []


@pytest.mark.parametrize(
    ("wheel_value", "project_value", "expected"),
    [
        (None, ">=3.10,<3.15", "wheel Requires-Python is missing"),
        (">=3.10", ">=3.10,<3.15", "incorrectly admits Python 3.15"),
        (">=3.11,<3.15", ">=3.10,<3.15", "rejects claimed Python 3.10"),
        (">=3.10,<3.15", ">=3.10", "pyproject.toml Requires-Python"),
        (">=3.10,<3.14", ">=3.10,<3.15", "rejects claimed Python 3.14"),
    ],
)
def test_requires_python_validation_rejects_unsafe_boundaries(
    tmp_path: Path,
    wheel_value: str | None,
    project_value: str,
    expected: str,
) -> None:
    failures = _requires_python_failures(
        _metadata(wheel_value), _pyproject(tmp_path, project_value)
    )

    assert any(expected in failure for failure in failures)


def test_source_license_metadata_and_canonical_text_are_exact() -> None:
    project_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project_data["build-system"]["requires"] == ["setuptools>=77"]
    assert project_data["project"]["license"] == "MIT"
    assert project_data["project"]["license-files"] == ["LICENSE"]
    assert not any(
        classifier.startswith("License ::")
        for classifier in project_data["project"]["classifiers"]
    )
    assert _source_license_failures(ROOT / "pyproject.toml", ROOT / "LICENSE") == []


@pytest.mark.parametrize(
    ("expression", "license_files", "classifier", "expected"),
    [
        ("Apache-2.0", '["LICENSE"]', "", "project.license"),
        ("MIT", '["COPYING"]', "", "project.license-files"),
        ("MIT", '["LICENSE"]', "License :: OSI Approved :: MIT License", "legacy"),
    ],
)
def test_source_license_validation_rejects_metadata_regressions(
    tmp_path: Path,
    expression: str,
    license_files: str,
    classifier: str,
    expected: str,
) -> None:
    license_path = tmp_path / "LICENSE"
    license_path.write_text((ROOT / "LICENSE").read_text(encoding="utf-8"), encoding="utf-8")

    failures = _source_license_failures(
        _license_metadata(
            tmp_path,
            expression=expression,
            license_files=license_files,
            classifier=classifier,
        ),
        license_path,
    )

    assert any(expected in failure for failure in failures)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("João Pedro Rosa dos Santos", "GitHub User"),
        ("2026", "2025"),
    ],
)
def test_source_license_validation_rejects_wrong_holder_or_year(
    tmp_path: Path, old: str, new: str
) -> None:
    license_path = tmp_path / "LICENSE"
    license_path.write_text(
        (ROOT / "LICENSE").read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )

    failures = _source_license_failures(_license_metadata(tmp_path), license_path)

    assert any("exact 2026 copyright holder" in failure for failure in failures)


def test_wheel_and_sdist_license_contracts() -> None:
    metadata = Message()
    metadata["License-Expression"] = "MIT"
    wheel_names = {"beets_noqlenmeta-1.0.0.dist-info/licenses/LICENSE"}
    sdist_names = {"beets_noqlenmeta-1.0.0/LICENSE"}

    assert _wheel_license_failures(metadata, wheel_names) == []
    assert _sdist_license_failures(sdist_names) == []


def test_archive_license_validation_rejects_missing_or_wrong_data() -> None:
    metadata = Message()
    metadata["License-Expression"] = "Apache-2.0"

    failures = _wheel_license_failures(metadata, set())
    assert any("License-Expression" in failure for failure in failures)
    assert any("licenses/LICENSE" in failure for failure in failures)
    assert _sdist_license_failures(set())
    assert _sdist_license_failures({"beets_noqlenmeta-1.0.0/package/LICENSE"})


def test_python_metadata_docs_and_ci_matrix_agree() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    classifiers = sorted(
        classifier.rsplit(" :: ", 1)[-1]
        for classifier in project["classifiers"]
        if classifier.startswith("Programming Language :: Python :: 3.")
    )
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    compatibility = (ROOT / "site-docs/reference/compatibility.md").read_text(
        encoding="utf-8"
    )

    assert SpecifierSet(project["requires-python"]) == EXPECTED_SPECIFIER
    assert classifiers == EXPECTED_PYTHONS
    matrix_line = next(line for line in ci.splitlines() if "python-version: [" in line)
    assert [version for version in EXPECTED_PYTHONS if f'"{version}"' in matrix_line] == (
        EXPECTED_PYTHONS
    )
    assert "3.15" not in matrix_line
    assert "Python 3.10 through 3.14" in compatibility
    assert "Python 3.15 is not claimed" in compatibility


def test_release_workflow_requires_tag_on_main_before_single_build() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    trigger = workflow.split("permissions:", 1)[0]
    ancestry_step = workflow.split(
        "- name: Verify release commit is contained in main", 1
    )[1].split("- uses: actions/setup-python", 1)[0]
    ancestry_index = workflow.index("git merge-base --is-ancestor")
    version_index = workflow.index("- name: Verify tag matches package version")
    build_index = workflow.index("python -m build")
    publish_boundary = workflow.split("uses: pypa/gh-action-pypi-publish@release/v1", 1)[1]

    assert 'tags:\n      - "v*"' in trigger
    assert "branches:" not in trigger
    assert "pull_request:" not in trigger
    assert "workflow_dispatch:" not in trigger
    assert "tag != f\"v{version}\"" in workflow
    assert "fetch-depth: 0" in workflow
    assert "persist-credentials: false" in workflow
    assert "git fetch" not in workflow
    assert "git show-ref --verify --quiet refs/remotes/origin/main" in ancestry_step
    assert 'git rev-parse "${RELEASE_TAG}^{commit}"' in ancestry_step
    assert 'git rev-parse "refs/remotes/origin/main^{commit}"' in ancestry_step
    assert '"${tag_commit}"' in ancestry_step
    assert '"${main_commit}"' in ancestry_step
    assert ancestry_step.index("git show-ref") < ancestry_step.index("tag_commit=")
    assert ancestry_step.index("tag_commit=") < ancestry_step.index("main_commit=")
    assert ancestry_step.index("main_commit=") < ancestry_step.index("git merge-base")
    assert ancestry_index < version_index < build_index
    assert workflow.count("python -m build") == 1
    assert "needs: build" in workflow
    assert "id-token: write" in workflow
    assert "secrets." not in workflow
    assert "github.token" not in workflow
    assert "actions/upload-artifact@v5" in workflow
    assert "actions/download-artifact@v6" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "uses:" not in publish_boundary
    assert "run:" not in publish_boundary


def test_release_checklist_records_completed_v1_release() -> None:
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    completed = (
        "[x] Read the Docs project imported and public `latest`, `stable`, and "
        "`v1.0.0` builds passed.",
        "[x] PyPI project ownership established by the first successful publication.",
        "[x] PyPI Trusted Publisher configured",
        "[x] GitHub environment `pypi` configured with the `v*` deployment tag rule.",
        "[x] Repository security/private vulnerability reporting route confirmed.",
        "[x] `v1.0.0` tag created",
        "[x] Tag version exactly matches",
        "[x] Tag resolves to a commit contained in remote `main`",
        "[x] Tag workflow built, checked, and published",
        "[x] No API token or long-lived publishing credential was used.",
        "[x] PyPI project name, version, `Requires-Python`, filenames, and file count are correct.",
        "[x] Published wheel and sdist hashes match the workflow artifacts",
        "[x] GitHub Release `v1.0.0` was created from the existing tag.",
        "[x] Read the Docs `stable`, `latest`, and `v1.0.0` versions are active and green.",
    )
    pending = (
        "[ ] PyPI rendered README has been visually reviewed.",
        "[ ] Public wheel installs in a clean environment and beets discovers `noqlenmeta`.",
        "[ ] `beet nm --help` works after the public clean install.",
    )

    assert all(item in checklist for item in completed)
    assert all(item in checklist for item in pending)
    assert "[ ] PyPI project ownership established by first publication." not in checklist
    assert "[ ] `v1.0.0` tag created" not in checklist
    assert "[ ] Tag workflow builds, checks, and publishes" not in checklist
