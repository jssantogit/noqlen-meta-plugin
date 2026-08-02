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
