# Noqlen Meta v2.0.1 Documentation Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare and publish Noqlen Meta `2.0.1` as a documentation-only patch release with the redesigned Documentation v2 in the stable release tag and a concise README landing page.

**Architecture:** Keep runtime code untouched. First lock the README shape with tests and update the public-doc validator, then bump release metadata and public release pages, add a focused `2.0.1` checklist, run the complete repository gate, merge through a PR, and finally perform the owner-authorized tag/publication/Read the Docs verification sequence.

**Tech Stack:** Python 3.10-3.14, beets `>=2.12,<3`, MkDocs Material, pytest, Ruff, setuptools/build, Twine, Git/GitHub Actions, PyPI Trusted Publishing, Read the Docs.

## Global Constraints

- Release version is exactly `2.0.1`.
- Release date is `2026-08-12`.
- Public README structure is exactly `# Noqlen Meta` -> summary -> `## Capabilities` -> `## Installation`.
- README must not contain a published-version banner, `Documentation`, `First Preview`, or `License` section.
- README must not hard-code `2.0.1` or any future release number.
- `LICENSE` and package MIT metadata remain unchanged and authoritative even though README no longer has a License section.
- No files under `beetsplug/noqlenmeta` may change.
- No dependency, Python, beets, provider, command, field, configuration-default, identity, AcoustID, or enrichment behavior changes are allowed.
- Existing Documentation v2 information architecture stays unchanged.
- The existing `v2.0.0` tag is immutable and must not be moved or retagged.
- Do not weaken documentation, release, package, or CI validation to make the release pass.
- `site-docs/examples/full-config.yaml` must remain machine-equal to `default_config()`.
- Release tags must be contained in remote `main` and exactly match `project.version`; the existing release workflow remains the publication mechanism.
- PyPI publication uses Trusted Publishing/OIDC; do not add long-lived credentials.
- Read the Docs `latest` remains the branch build and `stable` remains release-oriented; do not artificially alias them together.
- Execution branch: `release/v2.0.1-docs`.

## File Map

- `README.md` — concise GitHub/PyPI landing page only.
- `tests/docs/test_public_documentation.py` — README shape and public release-state contract.
- `scripts/check_public_docs.py` — machine gate for README shape, exact public interfaces, release metadata, links, safety language, and docs navigation.
- `pyproject.toml` — package version changes from `2.0.0` to `2.0.1`; all other package contracts remain unchanged.
- `CHANGELOG.md` — canonical dated `2.0.1` documentation-patch record.
- `site-docs/index.md` — public docs home release line updated to `2.0.1`.
- `site-docs/project/release.md` — current release and GitHub Release URL updated to `2.0.1` while preserving release/safety/process facts.
- `site-docs/project/changelog.md` — removes stale pre-v2 publication wording and describes the canonical changelog order accurately.
- `RELEASE_CHECKLIST.md` — adds a focused `2.0.1` candidate/execution/post-release section without rewriting historical records.
- `tests/release/test_release_contracts.py` — explicit active-version contract plus unchanged Python/license/workflow guarantees.
- `.github/workflows/release.yml` — read-only for this release unless a test exposes a real contradiction; no release-workflow redesign is planned.

---

### Task 1: Make README a concise landing page and update its machine contract

**Files:**
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `scripts/check_public_docs.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: approved README design from `docs/superpowers/specs/2026-08-12-v2-0-1-docs-release-design.md`.
- Produces: a README whose only Markdown headings are `# Noqlen Meta`, `## Capabilities`, and `## Installation`; public-doc validation no longer requires README to duplicate release/manual/license links.

- [ ] **Step 1: Add a failing README structure test**

Add this focused test to `tests/docs/test_public_documentation.py`:

```python
def test_readme_is_concise_project_landing_page() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = [line for line in readme.splitlines() if line.startswith("#")]

    assert headings == ["# Noqlen Meta", "## Capabilities", "## Installation"]
    assert "## Documentation" not in readme
    assert "## First Preview" not in readme
    assert "## License" not in readme
    assert "Version `" not in readme
    assert "releases/tag/v" not in readme
    assert "pip install beets-noqlenmeta" in readme
    assert 'pip install "beets-noqlenmeta[discogs]"' in readme
    assert 'pip install "beets-noqlenmeta[audio]"' in readme
    assert "plugins:\n  - noqlenmeta" in readme
    assert "beet help noqlenmeta" in readme
```

Run:

```bash
pytest tests/docs/test_public_documentation.py::test_readme_is_concise_project_landing_page -q
```

Expected: FAIL because the current README still has Documentation, First Preview, and License/version content.

- [ ] **Step 2: Change `scripts/check_public_docs.py` from README-as-manual checks to README-shape checks**

Keep all exact CLI/config/full-config/nav/secret/safety/release-page checks. Make only these README-specific changes:

1. After the existing README length/internal-term check, validate headings and forbidden sections:

```python
readme_headings = [
    line for line in readme_text.splitlines() if line.startswith("#")
]
if readme_headings != ["# Noqlen Meta", "## Capabilities", "## Installation"]:
    failures.append("README does not use the approved landing-page structure")
for forbidden_heading in ("## Documentation", "## First Preview", "## License"):
    if forbidden_heading in readme_text:
        failures.append(f"README retains removed section: {forbidden_heading}")
if "Version `" in readme_text or "releases/tag/v" in readme_text:
    failures.append("README contains release-specific version metadata")
for required_install_text in (
    "pip install beets-noqlenmeta",
    'pip install "beets-noqlenmeta[discogs]"',
    'pip install "beets-noqlenmeta[audio]"',
    "plugins:\n  - noqlenmeta",
    "beet help noqlenmeta",
):
    if required_install_text not in readme_text:
        failures.append(f"README installation omits: {required_install_text}")
```

2. Remove the README-only MIT link requirement:

```python
if "[MIT License](LICENSE)" not in readme_text:
    ...
```

Do **not** remove the release-page MIT check or license/package tests.

3. Replace the README Read the Docs requirement with public-docs-only validation. Delete:

```python
if f"[Read the Docs]({READTHEDOCS_URL})" not in readme_text:
    failures.append("README does not link to the canonical live Read the Docs site")
```

Keep:

```python
if READTHEDOCS_URL not in public_text or "canonical public documentation is live" not in folded:
    failures.append("public docs do not identify the canonical live Read the Docs site")
```

4. Change PyPI validation from README + docs to docs only:

```python
if PYPI_URL not in public_text:
    failures.append("public docs do not link to the published PyPI project")
```

5. Remove the README version-publication assertion:

```python
if "version `2.0.0` is published on" not in readme_text.casefold():
    ...
```

Do not remove release-page/changelog/checklist release validation.

- [ ] **Step 3: Replace README with the approved concise content**

Use this exact structure and content, adjusting only line wrapping if needed for repository style:

```markdown
# Noqlen Meta

Noqlen Meta is a beets plugin for multi-provider metadata enrichment and
MusicBrainz identity tools. beets remains the matcher and library manager:
Noqlen enriches releases, tracks, and artists that beets has already selected,
with separate workflows for MusicBrainz identity and AcoustID evidence.

Ordinary enrichment previews by default. Database changes, verified artwork
application, and audio-file synchronization remain explicitly authorized rather
than happening implicitly.

## Capabilities

- Enrich release, track, and artist metadata with genres, styles, moods,
  languages, artist geography, and release details from focused providers.
- Retrieve supported plain lyrics from LRCLIB.
- Enrich importer-selected music and albums or standalone items already managed
  by a beets library.
- Select and apply verified Cover Art Archive artwork, including deterministic
  `cover.jpg` sidecars and optional embedding.
- Analyze local BPM with the optional `[audio]` extra and lazy Librosa support.
- Audit and repair MusicBrainz identity and use AcoustID fingerprints or
  recording evidence in explicit existing-library workflows.
- Synchronize supported ordinary metadata and BPM to audio files through the
  verified write path, with identity-tag synchronization kept separate.

## Installation

Install Noqlen Meta in the same Python environment as beets:

```bash
pip install beets-noqlenmeta
```

Discogs support uses the optional Discogs client:

```bash
pip install "beets-noqlenmeta[discogs]"
```

Optional local BPM analysis uses the audio extra:

```bash
pip install "beets-noqlenmeta[audio]"
```

Enable the plugin in the beets `config.yaml`:

```yaml
plugins:
  - noqlenmeta
```

Verify that beets loaded the plugin:

```bash
beet help noqlenmeta
```

`beet noqlenmeta` is the full command name; `beet nm` is the preferred alias.
```

Do not add a Documentation link, version banner, release badge, First Preview, configuration tutorial, or License section.

- [ ] **Step 4: Run the focused README/docs gate**

Run:

```bash
pytest tests/docs/test_public_documentation.py::test_readme_is_concise_project_landing_page -q
python scripts/check_public_docs.py
```

Expected: README test PASS. `check_public_docs.py` may still FAIL only on the intentional `2.0.0` release-state/version assertions that Task 2 updates; it must not fail on README Documentation/License/PyPI/Read the Docs requirements.

- [ ] **Step 5: Commit**

```bash
git add README.md scripts/check_public_docs.py tests/docs/test_public_documentation.py
git commit -m "docs: simplify project readme"
```

---

### Task 2: Bump the package and public release state to 2.0.1

**Files:**
- Modify: `tests/release/test_release_contracts.py`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `scripts/check_public_docs.py`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: `site-docs/index.md`
- Modify: `site-docs/project/release.md`
- Modify: `site-docs/project/changelog.md`

**Interfaces:**
- Consumes: unchanged packaging/release workflow and Documentation v2 already present on the branch.
- Produces: all active source/package/public-doc release metadata consistently identifies `2.0.1`; historical `2.0.0` records remain historical and unchanged.

- [ ] **Step 1: Add a failing active-version release test**

Add to `tests/release/test_release_contracts.py`:

```python
def test_active_project_version_is_2_0_1() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert project["version"] == "2.0.1"
```

Run:

```bash
pytest tests/release/test_release_contracts.py::test_active_project_version_is_2_0_1 -q
```

Expected: FAIL with `2.0.0 != 2.0.1`.

- [ ] **Step 2: Bump only `project.version` in `pyproject.toml`**

Change:

```toml
version = "2.0.0"
```

to:

```toml
version = "2.0.1"
```

Do not change dependencies, optional dependencies, classifiers, URLs, Python bounds, beets bounds, license, or package discovery.

- [ ] **Step 3: Add the canonical changelog entry**

Keep `## Unreleased` empty and insert immediately after it:

```markdown
## 2.0.1 - 2026-08-12

### Changed

- Redesigned beginner-first public documentation is included in the new stable
  release tag.
- Simplified the project README to a concise summary, capability list, and
  installation guide instead of duplicating the full manual.
- Corrected documentation and release metadata carried forward after `2.0.0`.
```

The order must become:

```text
Unreleased
2.0.1 - 2026-08-12
2.0.0 - 2026-08-11
1.0.0 - 2026-08-02
```

- [ ] **Step 4: Update public release pages without redesigning Documentation v2**

In `site-docs/index.md`, change only the final release sentence from version `2.0.0` to `2.0.1`.

In `site-docs/project/release.md`:

- change `Current stable release: 2.0.0 (2026-08-11)` to `2.0.1 (2026-08-12)`;
- change the current PyPI/GitHub Release wording and URL to `v2.0.1`;
- add a short `## Version 2.0.1` section before the historical `## Version 2.0.0` section explaining that 2.0.1 is a documentation-only patch containing Documentation v2, the concise README, and release/documentation metadata corrections;
- retain the full `## Version 2.0.0` feature history;
- change the explicit versioned Read the Docs verification note to `v2.0.1` for the active release, while leaving `v2.0.0` historical references only where they describe that historical release;
- preserve Publication, Documentation, and License facts.

Use this exact `2.0.1` paragraph:

```markdown
## Version 2.0.1

Version 2.0.1 is a documentation-only patch release. It ships the redesigned
beginner-first Documentation v2 as a stable release, reduces the repository and
PyPI README to a concise project landing page, and carries forward documentation
and release-metadata corrections made after 2.0.0. Runtime behavior is unchanged.
```

In `site-docs/project/changelog.md`, replace the stale text about `1.0.0` being the current published release with:

```markdown
The canonical changelog contains an empty `Unreleased` section followed by the
`2.0.1 - 2026-08-12`, `2.0.0 - 2026-08-11`, and historical `1.0.0` release
records. Version 2.0.1 is the current stable release.
```

- [ ] **Step 5: Update `scripts/check_public_docs.py` to the active 2.0.1 contract**

Make these exact release-state changes:

```python
GITHUB_RELEASE_URL = (
    "https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.1"
)
```

```python
if project["version"] != "2.0.1":
    failures.append("active package version is not 2.0.1")
```

Require the new changelog section/order:

```python
if "## 2.0.1 - 2026-08-12" not in changelog_text:
    failures.append("CHANGELOG.md does not contain the dated 2.0.1 release section")
elif not (
    changelog_text.index("## Unreleased")
    < changelog_text.index("## 2.0.1 - 2026-08-12")
    < changelog_text.index("## 2.0.0 - 2026-08-11")
    < changelog_text.index("## 1.0.0 - 2026-08-02")
):
    failures.append("CHANGELOG.md must order Unreleased, 2.0.1, 2.0.0, then 1.0.0")
```

Update `required_release_state` to:

```python
required_release_state = (
    "current stable release: `2.0.1` (2026-08-12)",
    "noqlen meta 2.0.1 is published on",
    "the read the docs project slug is `noqlen-meta`",
)
```

Change the GitHub Release failure wording from v2.0.0 to v2.0.1. Do not add the version back to README validation.

Keep historical v1.0.0/v2.0.0 checklist requirements as historical facts.

- [ ] **Step 6: Update the public release-state pytest contract**

In `test_public_release_state_is_consistent()`:

Remove these README-specific assertions because Task 1 intentionally removed them:

```python
assert "[MIT License](LICENSE)" in readme
assert "João Pedro Rosa dos Santos" in readme
assert "[Read the Docs](https://noqlen-meta.readthedocs.io/en/stable/)" in readme
assert "https://pypi.org/project/beets-noqlenmeta/" in readme
assert "Version `2.0.0` is published on" in readme
```

Do not remove the home/release MIT, PyPI, Read the Docs, permission-boundary, stale-host, or stale-state assertions.

Replace active-release assertions with:

```python
assert "## 2.0.1 - 2026-08-12" in changelog
assert (
    changelog.index("## Unreleased")
    < changelog.index("## 2.0.1 - 2026-08-12")
    < changelog.index("## 2.0.0 - 2026-08-11")
    < changelog.index("## 1.0.0 - 2026-08-02")
)
assert "Current stable release: `2.0.1` (2026-08-12)" in release
assert "Noqlen Meta 2.0.1 is published on" in release
assert "https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.1" in release
assert "Version 2.0.1 is the current stable release." in (
    ROOT / "site-docs/project/changelog.md"
).read_text(encoding="utf-8")
```

Keep the assertions that historical `2.0.0` changelog/checklist records still exist.

- [ ] **Step 7: Run release-state tests**

Run:

```bash
pytest tests/release/test_release_contracts.py::test_active_project_version_is_2_0_1 -q
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
```

Expected: PASS except for any intentionally missing `2.0.1` checklist requirements introduced in Task 3; no README/manual duplication failure is acceptable.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml CHANGELOG.md site-docs/index.md site-docs/project/release.md site-docs/project/changelog.md scripts/check_public_docs.py tests/docs/test_public_documentation.py tests/release/test_release_contracts.py
git commit -m "release: prepare version 2.0.1 metadata"
```

---

### Task 3: Add the focused v2.0.1 release checklist contract

**Files:**
- Modify: `RELEASE_CHECKLIST.md`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `scripts/check_public_docs.py`

**Interfaces:**
- Consumes: active version `2.0.1` from Task 2 and the unchanged trusted release workflow.
- Produces: an operational candidate/release/post-release checklist whose external steps can be checked after publication without weakening historical release evidence.

- [ ] **Step 1: Add a failing checklist-presence test**

Add to `tests/docs/test_public_documentation.py`:

```python
def test_v2_0_1_release_checklist_is_present() -> None:
    checklist = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "## Version 2.0.1 Documentation Release" in checklist
    assert "Package version is `2.0.1`." in checklist
    assert "README contains only the approved summary, Capabilities, and Installation structure." in checklist
    assert "Create `v2.0.1` tag on a commit contained in `main`." in checklist
    assert "Publish `2.0.1` to PyPI through Trusted Publishing." in checklist
    assert "Create and verify the GitHub Release for `v2.0.1`." in checklist
    assert "Read the Docs builds `v2.0.1` successfully." in checklist
    assert "`/en/stable/` displays the redesigned Documentation v2" in checklist
```

Run:

```bash
pytest tests/docs/test_public_documentation.py::test_v2_0_1_release_checklist_is_present -q
```

Expected: FAIL because the `2.0.1` section does not exist yet.

- [ ] **Step 2: Append the focused `2.0.1` checklist section**

Append exactly this section to `RELEASE_CHECKLIST.md`; do not rewrite historical v1/v2.0.0 sections:

```markdown
## Version 2.0.1 Documentation Release

### Candidate Preparation

- [x] Package version is `2.0.1`.
- [x] Changelog contains `2.0.1 - 2026-08-12`.
- [x] README contains only the approved summary, Capabilities, and Installation structure.
- [x] README contains no release-version banner, Documentation section, First Preview section, or License section.
- [x] Documentation v2 remains the public MkDocs information architecture.
- [x] Release-readiness diff contains no changes under `beetsplug/noqlenmeta`.
- [x] Full CI is green on the release pull request.

### Owner-Authorized Release Execution

- [ ] Merge the `2.0.1` release candidate into `main`.
- [ ] Confirm final `main` CI.
- [ ] Create `v2.0.1` tag on a commit contained in `main`.
- [ ] Allow the existing tag workflow to verify the tag/version match and publish through PyPI Trusted Publishing.
- [ ] Publish `2.0.1` to PyPI through Trusted Publishing.
- [ ] Create and verify the GitHub Release for `v2.0.1`.

### Post-Release Verification

- [ ] Verify the public PyPI `2.0.1` metadata and artifacts.
- [ ] Visually review the PyPI-rendered simplified README.
- [ ] Read the Docs builds `v2.0.1` successfully.
- [ ] `/en/stable/` displays the redesigned Documentation v2 rather than the old v2.0.0 manual.
- [ ] Public `beets-noqlenmeta==2.0.1` clean install discovers `noqlenmeta` and `beet nm --help` works.
```

The release-PR implementation may mark the first six Candidate Preparation items complete only after their corresponding changes/checks are true. Mark `Full CI is green on the release pull request` only after the PR CI is actually green; if the checklist is committed before PR CI, leave that one unchecked and update it in a final PR commit after CI succeeds.

- [ ] **Step 3: Make checklist validation state-tolerant for owner-controlled steps**

Do not require `[ ]` or `[x]` for `2.0.1` external steps, because their state changes after publication. In `scripts/check_public_docs.py`, add semantic phrase checks like:

```python
required_v2_0_1_checklist_phrases = (
    "## Version 2.0.1 Documentation Release",
    "Package version is `2.0.1`.",
    "README contains only the approved summary, Capabilities, and Installation structure.",
    "Create `v2.0.1` tag on a commit contained in `main`.",
    "Publish `2.0.1` to PyPI through Trusted Publishing.",
    "Create and verify the GitHub Release for `v2.0.1`.",
    "Read the Docs builds `v2.0.1` successfully.",
    "`/en/stable/` displays the redesigned Documentation v2",
)
for phrase in required_v2_0_1_checklist_phrases:
    if phrase not in checklist_text:
        failures.append(f"2.0.1 release checklist omits: {phrase}")
```

Keep all existing exact historical checklist assertions for completed v1.0.0/v2.0.0 state.

- [ ] **Step 4: Run checklist and public-doc gates**

Run:

```bash
pytest tests/docs/test_public_documentation.py::test_v2_0_1_release_checklist_is_present -q
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add RELEASE_CHECKLIST.md scripts/check_public_docs.py tests/docs/test_public_documentation.py
git commit -m "release: add v2.0.1 publication checklist"
```

---

### Task 4: Run the complete candidate verification gate and open the release PR

**Files:**
- Verify: entire repository
- Verify read-only runtime scope: `beetsplug/noqlenmeta/**`
- Potentially modify only: `RELEASE_CHECKLIST.md` to mark PR CI complete after it actually succeeds

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: a reviewable `release/v2.0.1-docs` PR whose final head has no runtime changes and passes the complete repository CI matrix.

- [ ] **Step 1: Run local/static repository verification**

Run from repository root:

```bash
python -m ruff check .
pytest -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: all PASS.

- [ ] **Step 2: Build and inspect distributions**

Clean stale build output first:

```bash
rm -rf build dist *.egg-info
python -m build
python -m twine check --strict dist/*
python scripts/check_distribution.py dist
```

Expected: PASS; built wheel/sdist identify version `2.0.1`, preserve `Requires-Python >=3.10,<3.15`, include the MIT license, and render the simplified README as package metadata.

- [ ] **Step 3: Prove runtime is untouched**

Run:

```bash
git diff main...HEAD -- beetsplug/noqlenmeta
```

Expected: no output.

Also inspect changed paths:

```bash
git diff --name-only main...HEAD
```

Expected changed implementation/release paths are limited to README, version/changelog/release docs/checklist/tests/validator and the approved Superpowers spec/plan. `.github/workflows/release.yml` should be unchanged.

- [ ] **Step 4: Remove generated artifacts before committing/opening PR**

Run:

```bash
rm -rf build dist *.egg-info site

git status --short
```

Expected: no generated build/site artifacts are staged or untracked.

- [ ] **Step 5: Open a PR to `main`**

Use title:

```text
release: prepare Noqlen Meta 2.0.1
```

Use a body that states:

```markdown
## Summary

- simplify the README to project summary, capabilities, and installation only
- bump package/release metadata to 2.0.1
- carry the already-merged Documentation v2 redesign into a new stable release tag
- add a focused 2.0.1 release/publication checklist

## Scope

- documentation/release-metadata patch only
- no changes under `beetsplug/noqlenmeta`
- no provider, command, configuration, dependency, Python, or beets behavior changes
- v2.0.0 remains immutable

## Release intent

After this PR is green and merged, verify final main CI, create `v2.0.1` on that main commit, allow the existing Trusted Publishing workflow to publish, create the GitHub Release, and verify Read the Docs `v2.0.1` plus `/en/stable/`.
```

- [ ] **Step 6: Wait for and inspect the complete PR CI matrix**

Required green lanes:

- documentation contract + `mkdocs build --strict`;
- Python 3.10;
- Python 3.11;
- Python 3.12;
- Python 3.13;
- Python 3.14;
- beets minimum `2.12.0`;
- beets latest below 3;
- audio-analysis/Librosa;
- package build/content/clean-install.

If any lane fails, fix the cause; do not weaken a test or validator unless it is enforcing a requirement explicitly removed by the approved README design.

- [ ] **Step 7: Mark the PR-CI candidate gate complete only after CI is green**

If `RELEASE_CHECKLIST.md` still contains:

```markdown
- [ ] Full CI is green on the release pull request.
```

change it to:

```markdown
- [x] Full CI is green on the release pull request.
```

Run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
```

Commit:

```bash
git add RELEASE_CHECKLIST.md
git commit -m "release: record green v2.0.1 candidate CI"
```

Then wait for the fresh CI on that final head and require it to be fully green too.

- [ ] **Step 8: Return the release-candidate handoff**

Report exactly:

```text
Branch: release/v2.0.1-docs
PR: <number>
Final candidate HEAD: <sha>
Package version: 2.0.1
Runtime diff under beetsplug/noqlenmeta: empty
PR CI: green
Remaining owner-authorized actions: merge -> final main CI -> v2.0.1 tag -> Trusted Publishing -> GitHub Release -> PyPI/Read the Docs verification
```

Do not tag or publish inside this task.

---

### Task 5: Perform owner-authorized v2.0.1 release execution and verification

**Files:**
- Modify after successful external release: `RELEASE_CHECKLIST.md` on `main` only, to record completed owner-controlled/post-release checks.
- Do not modify the immutable `v2.0.1` tag after creation.

**Interfaces:**
- Consumes: green release PR from Task 4 and explicit owner authorization to merge/tag/publish.
- Produces: published PyPI `2.0.1`, GitHub Release `v2.0.1`, successful Read the Docs versioned build, and `stable` displaying Documentation v2.

- [ ] **Step 1: Squash-merge the green release PR into `main`**

Use expected-head protection when the GitHub tooling supports it. Record the resulting `main` commit SHA.

- [ ] **Step 2: Require fresh final-main CI on the squash commit**

Do not tag until the push-triggered CI for that exact `main` SHA is completed with conclusion `success` across the full matrix.

- [ ] **Step 3: Create and push `v2.0.1` on the verified main commit**

If the current connector cannot create Git tags, the owner performs:

```bash
git fetch origin main --tags
git checkout main
git pull --ff-only origin main
git tag -a v2.0.1 <VERIFIED_MAIN_SHA> -m "Noqlen Meta v2.0.1"
git push origin v2.0.1
```

Before pushing, verify:

```bash
git merge-base --is-ancestor <VERIFIED_MAIN_SHA> origin/main
git show v2.0.1 --no-patch
```

The tag must resolve exactly to the verified release commit and must not move `v2.0.0`.

- [ ] **Step 4: Verify the existing Publish Release workflow**

Wait for the tag-triggered workflow. Require:

- ancestry verification passes;
- tag/package version equality passes;
- one build is produced and checked;
- wheel/sdist validation passes;
- PyPI Trusted Publishing succeeds through OIDC.

If publication fails, do not move/recreate the tag; investigate the workflow/publication failure from the immutable tag.

- [ ] **Step 5: Verify PyPI 2.0.1**

Confirm public PyPI shows:

- project `beets-noqlenmeta`;
- version `2.0.1`;
- Python requirement `>=3.10,<3.15`;
- expected wheel and sdist;
- simplified README with only Noqlen Meta summary, Capabilities, and Installation headings.

Perform a clean-install smoke test:

```bash
python -m venv /tmp/noqlenmeta-201
/tmp/noqlenmeta-201/bin/python -m pip install --upgrade pip
/tmp/noqlenmeta-201/bin/python -m pip install "beets-noqlenmeta==2.0.1"
/tmp/noqlenmeta-201/bin/beet help noqlenmeta
/tmp/noqlenmeta-201/bin/beet nm --help
```

Expected: installation succeeds and both beets commands resolve.

- [ ] **Step 6: Create the GitHub Release v2.0.1**

Create the GitHub Release from the existing immutable `v2.0.1` tag with concise notes derived from the `2.0.1` changelog entry. Do not repeat the full v2.0.0 feature list.

- [ ] **Step 7: Verify Read the Docs**

Require all of these facts before declaring completion:

1. Read the Docs recognizes `v2.0.1` as a version.
2. The `v2.0.1` build completes successfully.
3. `/en/stable/` displays the redesigned Documentation v2 navigation, including `Start Here`, `Configuration`, `Commands`, `Recipes`, `Troubleshooting`, `Technical Reference`, `Advanced`, and `Project`.
4. `/en/stable/` no longer shows the old v2.0.0 top-level `Getting Started`, `Concepts`, `How-to Guides`, and `Reference` navigation.
5. `latest` may continue to represent `main`; do not change alias semantics solely to make it equal `stable`.

If `v2.0.1` builds successfully but `stable` does not advance automatically, inspect the Read the Docs Versions/Automation Rules configuration before changing repository content or moving tags.

- [ ] **Step 8: Record completed release state on `main`**

After PyPI, GitHub Release, and Read the Docs checks are actually true, update only the `Version 2.0.1 Documentation Release` section of `RELEASE_CHECKLIST.md` from `[ ]` to `[x]` for completed steps.

Run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
```

Commit the post-release checklist update on a normal follow-up branch/PR or the repository's accepted documentation-only process. Do not move the already-created tag.

- [ ] **Step 9: Final completion report**

Report:

```text
v2.0.1 release commit: <sha>
PR: <number>
Final main CI: green
Publish Release workflow: green
PyPI 2.0.1: verified
GitHub Release v2.0.1: verified
Read the Docs v2.0.1: green
Read the Docs stable: Documentation v2 verified
v2.0.0 tag: unchanged
Runtime behavior: unchanged
```
