#!/usr/bin/env python3
"""Validate public documentation coverage against production interfaces."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

from beetsplug.noqlenmeta import NoqlenMetaPlugin
from beetsplug.noqlenmeta.configuration import default_config

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI job
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "site-docs"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_CHECKLIST = ROOT / "RELEASE_CHECKLIST.md"
COMMAND_REFERENCE = DOCS / "reference" / "commands.md"
CONFIG_REFERENCE = DOCS / "reference" / "configuration.md"
FULL_CONFIG = DOCS / "examples" / "full-config.yaml"
RELEASE_PAGE = DOCS / "project" / "release.md"
READTHEDOCS_URL = "https://noqlen-meta.readthedocs.io/en/stable/"
PYPI_URL = "https://pypi.org/project/beets-noqlenmeta/"
GITHUB_RELEASE_URL = (
    "https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.0"
)

FORBIDDEN_README_TERMS = (
    "Block 0",
    "Noqlen Playbook",
    "FieldDecision",
    "ChangePlan",
    "BeetsTargetPlan",
    "TrackTargetPlan",
    "handoff",
)
FORBIDDEN_PUBLIC_LINKS = (
    "docs/context/",
    "docs/specs/",
    "docs/adr/",
    "handoff.md",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
    re.compile(r"/(?:home|Users)/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
)
STALE_VISIBILITY_PHRASES = (
    "public visibility remains unconfirmed",
    "not complete until GitHub reports",
    "publication remains gated on public repository confirmation",
)
STALE_EXTERNAL_GATE_PHRASES = (
    "until the owner imports the project",
    "read the docs project is intended",
    "read the docs is not considered live",
    "owner still needs to import",
    "public build remains pending",
)
STALE_RELEASE_STATE_PHRASES = (
    "ready for the release tag",
    "package has not been published to pypi",
    "first successful oidc publication will create",
    "versioned read the docs `v1.0.0` build does not exist",
    "will not exist until the release tag is created",
    "creation of the `v1.0.0` tag",
    "repository release candidate: `2.0.0`",
    "currently published release: `1.0.0` (2026-08-02)",
    "main merge, tag, publication, and versioned documentation remain pending",
)
STALE_READTHEDOCS_HOST = "noqlen-meta-plugin.readthedocs.io"


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> Any:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _load_yaml(path: Path) -> Any:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def _leaf_paths(value: dict[str, Any], prefix: str = "noqlenmeta") -> dict[str, Any]:
    leaves: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}"
        if isinstance(child, dict) and child:
            leaves.update(_leaf_paths(child, path))
        else:
            leaves[path] = child
    return leaves


def _nav_paths(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [path for child in value for path in _nav_paths(child)]
    if isinstance(value, dict):
        return [path for child in value.values() for path in _nav_paths(child)]
    return []


def _public_markdown() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def check() -> list[str]:
    failures: list[str] = []
    command_text = COMMAND_REFERENCE.read_text(encoding="utf-8")
    config_text = CONFIG_REFERENCE.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")
    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    checklist_text = RELEASE_CHECKLIST.read_text(encoding="utf-8")
    release_text = RELEASE_PAGE.read_text(encoding="utf-8")
    public_pages = _public_markdown()
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in public_pages)
    folded = public_text.casefold()
    public_words = " ".join(public_text.split()).casefold()

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    if project["version"] != "2.0.0":
        failures.append("active package version is not 2.0.0")

    command = NoqlenMetaPlugin().commands()[0]
    long_options = sorted(
        option
        for parser_option in command.parser.option_list
        for option in parser_option._long_opts
        if option != "--help"
    )
    for option in long_options:
        if f"`{option}`" not in command_text:
            failures.append(f"command reference omits {option}")

    defaults = default_config()
    for path in _leaf_paths(defaults):
        if f"`{path}`" not in config_text:
            failures.append(f"configuration reference omits {path}")

    full_config = _load_yaml(FULL_CONFIG)
    if not isinstance(full_config, dict) or full_config.get("noqlenmeta") != defaults:
        failures.append("full-config.yaml does not exactly match production defaults")
    for example in sorted((DOCS / "examples").glob("*.yaml")):
        try:
            parsed = _load_yaml(example)
        except yaml.YAMLError as error:
            failures.append(f"example YAML does not parse: {example.name}: {error}")
        else:
            if not isinstance(parsed, dict):
                failures.append(f"example YAML is not a mapping: {example.name}")

    mkdocs = _load_yaml(ROOT / "mkdocs.yml")
    nav_paths = _nav_paths(mkdocs.get("nav", []))
    for relative in nav_paths:
        if not (DOCS / relative).is_file():
            failures.append(f"navigation target does not exist: {relative}")
    nav_markdown = {path for path in nav_paths if path.endswith(".md")}
    actual_markdown = {str(path.relative_to(DOCS)) for path in public_pages}
    omitted = sorted(actual_markdown - nav_markdown)
    if omitted:
        failures.append(f"public Markdown omitted from nav: {', '.join(omitted)}")

    readme_lines = len(readme_text.splitlines())
    if readme_lines > 500:
        failures.append(f"README exceeds 500 lines: {readme_lines}")
    for term in FORBIDDEN_README_TERMS:
        if term.casefold() in readme_text.casefold():
            failures.append(f"README contains internal term: {term}")
    if "[MIT License](LICENSE)" not in readme_text:
        failures.append("README does not identify and link the MIT License")
    if "MIT License" not in release_text:
        failures.append("release documentation does not identify the MIT License")
    if "[x] MIT License selected and added" not in checklist_text:
        failures.append("release checklist does not mark the MIT decision complete")
    if "[x] Repository visibility changed to public" not in checklist_text:
        failures.append("release checklist does not mark public visibility complete")
    if "[ ] Repository visibility changed to public" in checklist_text:
        failures.append("release checklist retains the stale pending visibility gate")

    public_release_text = f"{readme_text}\n{public_text}".casefold()
    for phrase in STALE_VISIBILITY_PHRASES:
        if phrase in public_release_text:
            failures.append(f"public release text retains stale visibility phrase: {phrase}")
    if f"[Read the Docs]({READTHEDOCS_URL})" not in readme_text:
        failures.append("README does not link to the canonical live Read the Docs site")
    if READTHEDOCS_URL not in public_text or "canonical public documentation is live" not in folded:
        failures.append("public docs do not identify the canonical live Read the Docs site")
    if STALE_READTHEDOCS_HOST in public_release_text:
        failures.append("public docs retain the obsolete Read the Docs hostname")
    for phrase in STALE_EXTERNAL_GATE_PHRASES:
        if phrase in public_release_text:
            failures.append(f"public release text retains stale external gate phrase: {phrase}")
    for phrase in STALE_RELEASE_STATE_PHRASES:
        if phrase in public_release_text:
            failures.append(f"public release text retains stale release phrase: {phrase}")

    required_checklist_items = (
        (
            "[x] Read the Docs project imported and public `latest`, `stable`, and "
            "`v1.0.0` builds passed."
        ),
        "[x] PyPI project ownership established by the first successful publication.",
        "[x] PyPI Trusted Publisher configured",
        "[x] GitHub environment `pypi` configured with the `v*` deployment tag rule.",
        "[x] Repository security/private vulnerability reporting route confirmed.",
        "[x] `v1.0.0` tag created",
        "[x] Tag workflow built, checked, and published",
        "[x] No API token or long-lived publishing credential was used.",
        "[x] Published wheel and sdist hashes match the workflow artifacts",
        "[x] GitHub Release `v1.0.0` was created from the existing tag.",
        "[x] Read the Docs `stable`, `latest`, and `v1.0.0` versions are active and green.",
        "[x] Merge the v2 release candidate into `main`.",
        "[x] Confirm final `main` CI.",
        "[x] Create `v2.0.0` tag on a commit contained in `main`.",
        "[x] Allow the tag workflow to build and publish through PyPI Trusted Publishing.",
        "[x] Create and verify the GitHub Release for `v2.0.0`.",
        "[x] Publish `2.0.0` to PyPI and verify its artifacts.",
        (
            "[x] Confirm the canonical Read the Docs project at "
            "`noqlen-meta.readthedocs.io` and the public `stable` URL."
        ),
        (
            "[ ] Verify the explicit versioned Read the Docs `v2.0.0` build, "
            "if retained as a public version."
        ),
        "[ ] Public wheel installs in a clean environment and beets discovers `noqlenmeta`.",
        "[ ] `beet nm --help` works after the public clean install.",
    )
    for item in required_checklist_items:
        if item not in checklist_text:
            failures.append(f"release checklist omits required state: {item}")

    if PYPI_URL not in readme_text or PYPI_URL not in public_text:
        failures.append("public release text does not link to the published PyPI project")
    if GITHUB_RELEASE_URL not in public_text:
        failures.append("public release text does not link to the v2.0.0 GitHub Release")
    if "version `2.0.0` is published on" not in readme_text.casefold():
        failures.append("README does not record the v2.0.0 PyPI publication")
    if "## Unreleased" not in changelog_text:
        failures.append("CHANGELOG.md does not contain an Unreleased section")
    if "## 2.0.0 - 2026-08-11" not in changelog_text:
        failures.append("CHANGELOG.md does not contain the dated 2.0.0 release section")
    elif not (
        changelog_text.index("## Unreleased")
        < changelog_text.index("## 2.0.0 - 2026-08-11")
        < changelog_text.index("## 1.0.0 - 2026-08-02")
    ):
        failures.append("CHANGELOG.md must order Unreleased, 2.0.0, then 1.0.0")

    required_release_state = (
        "current stable release: `2.0.0` (2026-08-11)",
        "noqlen meta 2.0.0 is published on",
        "the read the docs project slug is `noqlen-meta`",
    )
    for phrase in required_release_state:
        if phrase not in public_words:
            failures.append(f"public docs omit v2 published state: {phrase}")

    required_distinctions = (
        "`--apply`",
        "`--write`",
        "`import.write`",
        "native `beet write`",
        "strict",
        "partial",
        "partial is not force",
        "`providers.musicbrainz.enabled`",
    )
    for phrase in required_distinctions:
        if phrase.casefold() not in folded:
            failures.append(f"public docs omit required distinction: {phrase}")
    required_v2_permissions = (
        "verified `cover.jpg` sidecars may be written",
        "audio files remain unchanged unless `--write`",
        "adding `--write` never triggers another provider call",
    )
    for phrase in required_v2_permissions:
        if phrase not in public_words:
            failures.append(f"public docs omit v2 permission boundary: {phrase}")
    separate_musicbrainz = (
        "does not control this identity source",
        "neither enables nor disables identity audit",
    )
    if not any(statement in folded for statement in separate_musicbrainz):
        failures.append("public docs do not separate MusicBrainz enrichment from identity audit")

    for link in FORBIDDEN_PUBLIC_LINKS:
        if link.casefold() in folded:
            failures.append(f"public docs link to internal project material: {link}")
    for pattern in SECRET_PATTERNS:
        for page in public_pages:
            if pattern.search(page.read_text(encoding="utf-8")):
                failures.append(f"possible secret or private path in {page.relative_to(ROOT)}")

    return failures


def main() -> int:
    failures = check()
    if failures:
        print("FAIL: public documentation validation")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: public documentation matches production interfaces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
