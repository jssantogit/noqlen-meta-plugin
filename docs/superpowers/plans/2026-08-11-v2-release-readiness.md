# Noqlen Meta v2 Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the integrated v2 branch into a truthful, test-backed `2.0.0` release candidate without changing product behavior or publishing anything.

**Architecture:** Keep production behavior frozen. Change only release metadata, changelog/checklist/public documentation, documentation validators, release-contract tests, and stale umbrella-design wording so every public/release contract matches the already-integrated v2 implementation. The release workflow itself remains unchanged and publication stays gated behind an explicit later merge-to-main + `v2.0.0` tag.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, pytest, Ruff, MkDocs, setuptools/build, Twine, GitHub Actions.

## Global Constraints

- Branch: `chore/v2-release-readiness`.
- Integration base: `docs/v2-enrichment-design` at `5db79cb64c35cb81f927316ef514c6020947fa80`.
- Approved spec: `docs/superpowers/specs/2026-08-11-v2-release-readiness-design.md` at commit `f3dd0938d118ccc297c86023525151413b9476c0`.
- Target package version: exactly `2.0.0`.
- Functional v2 code is frozen for this pass.
- Do not add/remove providers, analyzers, fields, commands, flags, config keys, defaults, or product behavior.
- Do not refactor enrichment, identity, AcoustID, artwork, BPM, importer, resolver, or file-sync code.
- Do not alter `.github/workflows/release.yml` unless a test proves the existing trusted-publishing security contract is broken; otherwise leave it byte-for-byte unchanged.
- Do not merge into `main`.
- Do not create `v2.0.0` tag, GitHub Release, PyPI upload, or Read the Docs stable/version alias.
- Public docs must distinguish prepared repository version `2.0.0` from the currently published `1.0.0` until release execution actually happens.
- Ordinary `--apply` may mutate the beets database and verified `cover.jpg`/`Album.artpath`; it must not mutate audio files without `--write`.
- Adding `--write` must remain documented as not expanding provider/network/analyzer work.
- Initial v2 BPM has no external provider: optional local Librosa only, disabled by default.
- Preserve Python support `>=3.10,<3.15`, CI matrix 3.10-3.14, beets 2.12.0/latest `<3`, MIT/OIDC release security, identity/AcoustID isolation, and no force mode.

## File Structure

Expected modifications only:

```text
pyproject.toml
CHANGELOG.md
RELEASE_CHECKLIST.md
README.md
scripts/check_public_docs.py
site-docs/index.md
site-docs/project/release.md
site-docs/project/changelog.md
site-docs/concepts/preview-apply-write.md        # only if needed for wording consistency
site-docs/reference/commands.md                  # only if a contradiction remains
docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md
tests/release/test_release_contracts.py
tests/docs/test_public_documentation.py          # only where public contract assertions belong
```

Do not touch `beetsplug/noqlenmeta/**` during this pass. If implementation appears to require production-code changes, stop and report the discrepancy instead of widening scope.

---

### Task 1: Freeze the 2.0.0 release-candidate contract

**Files:**
- Modify: `tests/release/test_release_contracts.py`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: `RELEASE_CHECKLIST.md`

**Interfaces:**
- Consumes: current v1 release-history contracts and the approved release-readiness spec.
- Produces: exact package version `2.0.0`, canonical v2 changelog ordering, and a checklist that separates completed v1 history from not-yet-authorized v2 publication steps.

- [ ] **Step 1: Add RED tests for active package version and changelog order**

Add tests equivalent to:

```python
def test_v2_release_candidate_version_is_exact() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == "2.0.0"


def test_changelog_orders_unreleased_v2_and_v1() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## Unreleased" in text
    assert "## 2.0.0 - 2026-08-11" in text
    assert "## 1.0.0 - 2026-08-02" in text
    assert text.index("## Unreleased") < text.index("## 2.0.0 - 2026-08-11")
    assert text.index("## 2.0.0 - 2026-08-11") < text.index("## 1.0.0 - 2026-08-02")
```

Also assert the v2 section contains representative user-facing phrases for semantic enrichment, Cover Art Archive, Librosa/BPM, ordinary file synchronization, AcoustID, and safety/no-force. Do not assert internal commit/task names.

- [ ] **Step 2: Add RED tests for the v2 checklist boundary**

Add a focused test that requires a dedicated v2 section and keeps future external actions unchecked:

```python
def test_v2_release_checklist_prepares_but_does_not_publish() -> None:
    text = (ROOT / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    assert "## Version 2.0.0 Release Candidate" in text
    assert "[x] Package version is `2.0.0`." in text
    assert "[x] Changelog contains `2.0.0 - 2026-08-11`." in text
    for pending in (
        "Merge the v2 release candidate into `main`.",
        "Create `v2.0.0` tag",
        "Publish `2.0.0` to PyPI",
        "Verify the versioned Read the Docs 2.0.0 build",
    ):
        assert f"[ ] {pending}" in text
```

Choose exact checklist wording once and make tests/document use the same strings. Preserve all historical v1 assertions already in the test file.

- [ ] **Step 3: Run focused tests and confirm RED state**

Run:

```bash
pytest -q tests/release/test_release_contracts.py
```

Expected: FAIL on version/changelog/checklist assertions while existing v1 historical/security tests continue to execute.

- [ ] **Step 4: Change only the package version**

In `pyproject.toml`:

```toml
version = "2.0.0"
```

Do not change dependencies, Python bounds, classifiers, extras, package discovery, or build-system requirements.

- [ ] **Step 5: Rewrite the top of CHANGELOG.md as a truthful v2 release record**

Required order:

```markdown
## Unreleased

## 2.0.0 - 2026-08-11

### Added
...

### Changed
...

### Safety
...

## 1.0.0 - 2026-08-02
```

Move the existing AcoustID `Unreleased` bullets into the new `2.0.0` section and add concise bullets for:

```text
release/track/artist semantic enrichment
multivalued styles/moods + semantic language/geography fields
genre taxonomy/style promotion
ordinary verified file synchronization behind --apply --write
CAA album artwork with cover.jpg/artpath/multidisc/optional embedding
opt-in lazy Librosa BPM via [audio]
existing-library AcoustID evidence since v1
```

Changed/Safety must explicitly preserve:

```text
--apply may write authorized cover.jpg sidecars/artpath but not audio files
--write adds file mutation authority without adding provider/analyzer work
local BPM is opt-in and preserves existing BPM by default
preview is non-mutating
identity/AcoustID remain isolated
no force mode
```

- [ ] **Step 6: Extend RELEASE_CHECKLIST.md without rewriting v1 history**

Append a new `## Version 2.0.0 Release Candidate` section with two subsections:

```markdown
### Candidate Preparation
### Owner-Authorized Release Execution
```

Candidate preparation items may initially remain unchecked except facts made true in this task (version/changelog). Publication/main/tag/PyPI/GitHub Release/Read the Docs version items must remain unchecked.

- [ ] **Step 7: Run focused tests GREEN and commit**

Run:

```bash
pytest -q tests/release/test_release_contracts.py
ruff check tests/release/test_release_contracts.py
```

Expected: PASS.

Commit:

```bash
git add pyproject.toml CHANGELOG.md RELEASE_CHECKLIST.md tests/release/test_release_contracts.py
git commit -m "chore: prepare v2 release contract"
```

---

### Task 2: Align public docs and validator with the real v2 permission model

**Files:**
- Modify: `scripts/check_public_docs.py`
- Modify: `tests/docs/test_public_documentation.py` only where helpful for direct contract coverage
- Modify: `README.md`
- Modify: `site-docs/index.md`
- Modify: `site-docs/project/release.md`
- Modify: `site-docs/project/changelog.md`
- Modify: `site-docs/concepts/preview-apply-write.md` if needed
- Modify: `site-docs/reference/commands.md` only if needed to remove contradiction

**Interfaces:**
- Consumes: production defaults/CLI introspection already used by `check_public_docs.py` and Task 1's version/changelog/checklist state.
- Produces: public documentation that describes v2 repository behavior while truthfully retaining 1.0.0 as the currently published release until later publication.

- [ ] **Step 1: Add RED validator assertions for v2 release-candidate truthfulness**

Update `scripts/check_public_docs.py` so its contract requires all of the following:

```text
pyproject active version == 2.0.0
CHANGELOG contains ## 2.0.0 - 2026-08-11
public text identifies 2.0.0 as prepared/release-candidate, not published
public text still identifies 1.0.0 as the currently published PyPI/GitHub release
ordinary --apply may write verified cover.jpg sidecars/Album.artpath
ordinary --apply does not mutate audio files without --write
--write does not expand provider/analysis work
```

Keep the historical constants/links for public `v1.0.0` PyPI/GitHub/Read the Docs state until v2 publication. Add a parsed active-version check rather than replacing historical v1 URLs with fictional v2 URLs.

Replace the old blanket `database_only_apply` validation with a v2 permission-boundary check. For example, require folded public text to contain concepts equivalent to:

```python
required_v2_permissions = (
    "verified `cover.jpg`",
    "audio files remain unchanged unless `--write`",
    "adding `--write` never triggers another provider call",
)
```

Use exact phrases that actually appear in the canonical public pages and keep them stable/testable.

- [ ] **Step 2: Add/adjust documentation tests before changing prose**

Where `tests/docs/test_public_documentation.py` already tests checker behavior, add focused assertions for the new release-candidate/version/permission rules. If that file only delegates to `check()`, prefer strengthening `check()` rather than duplicating it.

Run:

```bash
pytest -q tests/docs/test_public_documentation.py
python scripts/check_public_docs.py
```

Expected: FAIL until public text is aligned.

- [ ] **Step 3: Update README.md capability/release wording**

Keep the README user-facing and concise. It must accurately include current v2 repository capabilities:

```text
semantic release/track/artist enrichment
genre/style/mood/language/geography enrichment
ordinary verified file sync
CAA artwork
optional [audio] Librosa BPM
identity + AcoustID workflows
```

Add a short release-state sentence equivalent to:

```text
The repository is preparing Noqlen Meta 2.0.0. The currently published PyPI/GitHub release remains 1.0.0 until the v2 release workflow is explicitly executed after merge to main.
```

Do not claim v2 PyPI/GitHub Release/Read the Docs version exists.

- [ ] **Step 4: Update public release/status pages**

`site-docs/project/release.md` must lead with a two-state model:

```text
Repository release candidate: 2.0.0
Currently published release: 1.0.0 (2026-08-02)
```

Keep the v1 publication facts and links, then add a v2 candidate section stating that main merge/tag/publication/versioned docs are still pending and owner-authorized.

`site-docs/project/changelog.md` must say the root changelog now includes prepared `2.0.0` plus an empty `Unreleased` section while published release remains 1.0.0.

`site-docs/index.md` should describe v2 capabilities if it still reads like a v1-only landing page; retain truthful published-version links.

- [ ] **Step 5: Remove stale blanket database-only language**

Use `site-docs/reference/commands.md` as canonical matrix. Ensure public docs agree on:

```text
preview -> no mutation
--apply -> ordinary DB + authorized cover.jpg/artpath, no audio-file mutation
--apply --write -> same prepared work + supported tags/BPM + prepared cover embedding
--write -> no extra provider/analyzer work
```

Update `site-docs/concepts/preview-apply-write.md` because its current `--apply grants a database permission`/`Neither writes audio files` wording can stay only if it also explains the artwork-sidecar exception clearly. Do not weaken identity/AcoustID mode distinctions.

- [ ] **Step 6: Run docs validation GREEN**

Run:

```bash
pytest -q tests/docs/test_public_documentation.py
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add README.md scripts/check_public_docs.py site-docs tests/docs/test_public_documentation.py
git commit -m "docs: align public contracts for v2 candidate"
```

Only add files actually changed.

---

### Task 3: Correct stale umbrella-design BPM wording without changing behavior

**Files:**
- Modify: `docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md`
- Test: use focused text assertions/search; no production code.

**Interfaces:**
- Consumes: approved `docs/superpowers/specs/2026-08-11-artwork-audio-design.md` as authority.
- Produces: umbrella design consistent with the shipped first-v2 BPM architecture.

- [ ] **Step 1: Identify every stale external-BPM statement**

Run:

```bash
grep -nEi "external.*BPM|provider BPM|BPM.*external|local.*conflict|conflict.*local" docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md
```

Review all matches. The known stale success criterion currently says BPM can use external evidence and local analysis with local preferred on conflict; this must not remain as a v2 requirement.

- [ ] **Step 2: Replace only the stale design claims**

The umbrella design must state the initial-v2 contract exactly:

```text
there is no external BPM provider in the first v2 release
Librosa is the only local BPM backend
local BPM is optional and disabled by default
future TempoObservation sources remain architecturally possible without being implemented now
```

Also update any implementation-decomposition wording that still says to add provider BPM observations in this release.

Do not alter Artwork + Audio implementation semantics beyond making the umbrella document defer to the approved dedicated spec.

- [ ] **Step 3: Verify no contradictory external-BPM requirement remains**

Run:

```bash
python - <<'PY'
from pathlib import Path
p = Path("docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md")
t = p.read_text(encoding="utf-8").casefold()
assert "there is no external bpm provider" in t
assert "librosa" in t
assert "disabled by default" in t
assert "bpm can use external evidence" not in t
assert "add provider bpm observations" not in t
PY
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md
git commit -m "docs: align umbrella v2 bpm contract"
```

---

### Task 4: Integrated release-candidate verification and PR gate

**Files:**
- Modify: `RELEASE_CHECKLIST.md` only to mark candidate-preparation checks proven by fresh evidence.
- No production code.

**Interfaces:**
- Consumes: Tasks 1-3 candidate HEAD.
- Produces: one auditable release-readiness branch/PR with fresh local/CI evidence and no unintended functional changes.

- [ ] **Step 1: Run the complete local release-candidate verification**

Use a clean working tree and run, in this order:

```bash
pytest -m "not live"
ruff check .
python scripts/check_repo_contamination.py
python scripts/check_public_docs.py
mkdocs build --strict
rm -rf dist build *.egg-info
python -m build
python -m twine check --strict dist/*
python scripts/check_distribution.py dist
pytest -q tests/test_tempo.py tests/test_tempo_librosa.py
```

Then run the package smoke test equivalent to CI:

```bash
python -m venv /tmp/noqlen-v2-smoke
/tmp/noqlen-v2-smoke/bin/python -m pip install dist/*.whl
/tmp/noqlen-v2-smoke/bin/python -c "import beetsplug.noqlenmeta"
/tmp/noqlen-v2-smoke/bin/beet -p noqlenmeta nm --help
```

Expected: every command exits 0. If the host platform cannot perform one CI-equivalent step, do not mark it complete locally; rely on GitHub CI only after PR and report the distinction.

- [ ] **Step 2: Confirm release workflow was not weakened**

Run:

```bash
git diff 5db79cb64c35cb81f927316ef514c6020947fa80 -- .github/workflows/release.yml
```

Expected: empty diff.

Also run:

```bash
pytest -q tests/release/test_release_contracts.py
```

Expected: PASS, including tag-on-main, version-match, one-build, OIDC/no-secret assertions.

- [ ] **Step 3: Confirm no production-code changes slipped into release-readiness**

Run:

```bash
git diff --name-only 5db79cb64c35cb81f927316ef514c6020947fa80...HEAD
```

Fail the task if any path under `beetsplug/noqlenmeta/` appears. The only expected paths are release metadata/docs/tests/spec/plan files named in this plan.

- [ ] **Step 4: Mark only proven candidate-preparation checklist items**

Update the v2 `Candidate Preparation` subsection based strictly on evidence from Steps 1-3. Leave all owner-authorized execution items unchecked.

Run again:

```bash
pytest -q tests/release/test_release_contracts.py tests/docs/test_public_documentation.py
python scripts/check_public_docs.py
```

Expected: PASS after checklist updates.

Commit:

```bash
git add RELEASE_CHECKLIST.md
git commit -m "chore: record v2 candidate verification"
```

Skip this commit if no checklist checkbox changed.

- [ ] **Step 5: Open a draft PR against the integration branch**

PR contract:

```text
base: docs/v2-enrichment-design
head: chore/v2-release-readiness
title: chore: prepare Noqlen Meta 2.0.0 release candidate
draft: true
```

Body must state:

```text
release-contract/docs/tests only
no product behavior changes
no main merge/tag/release/publication authorization
2.0.0 is prepared but 1.0.0 remains the currently published release
```

- [ ] **Step 6: Wait for GitHub CI in the same execution session and verify every lane**

Required successful jobs:

```text
Python 3.10
Python 3.11
Python 3.12
Python 3.13
Python 3.14
beets minimum-2.12.0
beets latest-below-3
audio-analysis
documentation
package
```

Do not declare candidate readiness while any required job is queued, running, skipped unexpectedly, cancelled, or failed.

- [ ] **Step 7: Final review gate**

Compare PR diff against `docs/v2-enrichment-design` and classify findings:

```text
Critical/Important -> fix before approval
Minor -> note; fix only if it improves release truthfulness without widening scope
```

Explicitly verify:

```text
pyproject version == 2.0.0
empty Unreleased above dated 2.0.0 changelog
v1 historical publication facts preserved
v2 publication actions remain unchecked
no beetsplug/noqlenmeta production files changed
release.yml unchanged
public apply/write/artwork boundary matches production
umbrella BPM design matches local-only Librosa initial v2
```

Only after all fresh evidence is green may the PR be recommended for squash merge into `docs/v2-enrichment-design`. Do not merge to `main`, tag, or publish.
