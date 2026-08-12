# Noqlen Meta Documentation v2 Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public Noqlen Meta documentation around a beginner-friendly user journey while preserving a precise, code-verified Technical Reference and removing stale v1-era claims.

**Architecture:** Keep runtime behavior untouched. Build a new user-facing layer (`Start Here`, `Configuration`, `Commands`, `Recipes`, symptom-oriented `Troubleshooting`) and migrate exact contracts into `Technical Reference`; move conceptual material into `Advanced`. Production code and tests are the factual source of truth, while `scripts/check_public_docs.py`, MkDocs strict mode, and existing release/documentation tests remain the enforcement boundary.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, MkDocs Material, YAML, pytest, Ruff, Git/GitHub Actions.

## Global Constraints

- Public documentation language is English only.
- Target reader has installed beets but may not understand beets configuration, query syntax, database-vs-file behavior, or importer details.
- Do not change Noqlen Meta runtime behavior, defaults, provider semantics, commands, flags, fields, or public configuration contracts.
- Do not turn the docs into a complete beets manual; explain only the beets context required for the current Noqlen task.
- Production code is the source of truth. Existing documentation is reusable material, not authority.
- Preserve precise technical documentation; move it out of the beginner path rather than deleting it.
- Keep one canonical home for each complete explanation. Other pages summarize and link.
- Keep preview non-mutating; ordinary `--apply` may update the beets database plus authorized artwork sidecars/`Album.artpath`; audio files remain unchanged unless ordinary enrichment uses `--apply --write`.
- Adding `--write` must never be documented as triggering another provider call or analysis pass.
- Identity, AcoustID, and identity-tag workflows remain separate from ordinary enrichment semantics and mutation authorities.
- Do not imply that `providers.musicbrainz.enabled` controls identity audit.
- Do not imply that Noqlen owns importer acoustic matching/submission; native beets/chroma owns that workflow.
- `site-docs/examples/full-config.yaml` must remain machine-equal to `default_config()`.
- The existing `v2.0.0` tag is immutable. Do not retag or move it.
- Do not weaken documentation validation or CI to make the rewrite pass.
- No documentation PR is mergeable until the full repository CI is green.
- Execution branch: `docs/v2-documentation-redesign`.
- Runtime source files are read-only truth sources for this work. If documentation work appears to require a runtime change, stop and report the contradiction instead of modifying runtime code.

## Source-of-Truth Map

Use these files before asserting behavior:

- Public defaults and validation: `beetsplug/noqlenmeta/configuration.py`
- CLI options, modes, ordinary library/import workflow: `beetsplug/noqlenmeta/__init__.py`
- Provider capabilities by release/track/artist scope: `beetsplug/noqlenmeta/providers/specs.py`
- Provider-specific behavior: `beetsplug/noqlenmeta/providers/*.py`
- Semantic MusicBrainz behavior: `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py`, `beetsplug/noqlenmeta/semantic_media.py`
- beets storage mapping: `beetsplug/noqlenmeta/beets_mapping.py`, `beetsplug/noqlenmeta/field_types.py`
- Ordinary file synchronization: `beetsplug/noqlenmeta/file_sync.py`
- Artwork selection/application: `beetsplug/noqlenmeta/artwork.py`, `beetsplug/noqlenmeta/artwork_application.py`
- Identity/AcoustID: `beetsplug/noqlenmeta/identity/`, `beetsplug/noqlenmeta/acoustid/`, plus `tests/identity/` and `tests/acoustid/`
- BPM/local audio analysis: tempo implementation plus `tests/test_tempo.py` and `tests/test_tempo_librosa.py`
- Public docs validator: `scripts/check_public_docs.py`
- Documentation tests: `tests/docs/test_public_documentation.py`
- Release-state assertions: `tests/release/test_release_contracts.py`

## Final Public File Structure

```text
site-docs/
├── index.md
├── start-here/
│   ├── index.md
│   ├── installation.md
│   ├── basic-configuration.md
│   ├── first-preview.md
│   ├── understanding-results.md
│   ├── apply-changes.md
│   └── write-files.md
├── configuration/
│   ├── index.md
│   ├── fields.md
│   ├── providers.md
│   ├── genres-styles.md
│   ├── moods.md
│   ├── artwork.md
│   ├── bpm.md
│   ├── lyrics-languages.md
│   ├── acoustid.md
│   ├── advanced-resolution.md
│   └── full-example.md
├── commands/
│   ├── index.md
│   ├── preview.md
│   ├── apply.md
│   ├── write-files.md
│   ├── whole-library.md
│   ├── identity.md
│   ├── acoustid.md
│   └── identity-tags.md
├── recipes/
│   ├── index.md
│   ├── existing-library.md
│   ├── import-enrichment.md
│   ├── artwork.md
│   ├── local-bpm.md
│   ├── lyrics-languages.md
│   ├── repair-musicbrainz-ids.md
│   └── whole-library.md
├── troubleshooting/
│   ├── index.md
│   ├── nothing-changed.md
│   ├── review-blocked.md
│   ├── providers.md
│   ├── file-writing.md
│   └── acoustid.md
├── technical-reference/
│   ├── index.md
│   ├── configuration.md
│   ├── command-line.md
│   ├── fields.md
│   ├── providers.md
│   ├── beets-interaction.md
│   └── compatibility.md
├── advanced/
│   ├── index.md
│   ├── database-vs-file-tags.md
│   ├── preview-apply-write.md
│   ├── strict-vs-partial.md
│   ├── provider-authority-resolution.md
│   ├── safety.md
│   └── architecture.md
├── examples/
│   ├── full-config.yaml
│   ├── minimal-config.yaml
│   └── starter-config.yaml
└── project/
    ├── changelog.md
    ├── contributing.md
    └── release.md
```

The old public directories `getting-started/`, `concepts/`, `guides/`, and `reference/` must be absent at completion.

---

### Task 1: Establish the Technical Reference as the verified factual layer

**Files:**
- Modify: `scripts/check_public_docs.py`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `mkdocs.yml`
- Move/rewrite: `site-docs/reference/index.md` -> `site-docs/technical-reference/index.md`
- Move/audit: `site-docs/reference/configuration.md` -> `site-docs/technical-reference/configuration.md`
- Move/audit: `site-docs/reference/commands.md` -> `site-docs/technical-reference/command-line.md`
- Move/rewrite: `site-docs/reference/fields.md` -> `site-docs/technical-reference/fields.md`
- Move/audit: `site-docs/reference/providers.md` -> `site-docs/technical-reference/providers.md`
- Move/audit: `site-docs/reference/beets-interaction.md` -> `site-docs/technical-reference/beets-interaction.md`
- Move/audit: `site-docs/reference/compatibility.md` -> `site-docs/technical-reference/compatibility.md`

**Interfaces:**
- Consumes: public CLI from `NoqlenMetaPlugin().commands()[0]`; configuration leaves from `default_config()`; provider capabilities from `providers/specs.py`.
- Produces: canonical paths `site-docs/technical-reference/command-line.md` and `site-docs/technical-reference/configuration.md`, which `scripts/check_public_docs.py` will validate for complete CLI/config coverage.

- [ ] **Step 1: Add structural test expectations before moving files**

In `tests/docs/test_public_documentation.py`, add a test that asserts the canonical technical-reference files exist and the old `site-docs/reference` directory does not exist after migration:

```python
def test_technical_reference_uses_canonical_paths() -> None:
    docs = ROOT / "site-docs"
    assert (docs / "technical-reference" / "configuration.md").is_file()
    assert (docs / "technical-reference" / "command-line.md").is_file()
    assert not (docs / "reference").exists()
```

Run:

```bash
pytest tests/docs/test_public_documentation.py::test_technical_reference_uses_canonical_paths -q
```

Expected: FAIL because the new directory does not exist yet.

- [ ] **Step 2: Move the existing reference files with Git history preserved**

Run:

```bash
mkdir -p site-docs/technical-reference
git mv site-docs/reference/index.md site-docs/technical-reference/index.md
git mv site-docs/reference/configuration.md site-docs/technical-reference/configuration.md
git mv site-docs/reference/commands.md site-docs/technical-reference/command-line.md
git mv site-docs/reference/fields.md site-docs/technical-reference/fields.md
git mv site-docs/reference/providers.md site-docs/technical-reference/providers.md
git mv site-docs/reference/beets-interaction.md site-docs/technical-reference/beets-interaction.md
git mv site-docs/reference/compatibility.md site-docs/technical-reference/compatibility.md
rmdir site-docs/reference
```

- [ ] **Step 3: Point the validator at the canonical paths without weakening checks**

Change only the canonical reference constants in `scripts/check_public_docs.py`:

```python
COMMAND_REFERENCE = DOCS / "technical-reference" / "command-line.md"
CONFIG_REFERENCE = DOCS / "technical-reference" / "configuration.md"
```

Retain all existing checks that enumerate CLI options, enumerate every `default_config()` leaf, parse YAML, require complete nav coverage, guard secrets/private paths/internal links, and verify release state.

- [ ] **Step 4: Audit and correct the exact Technical Reference against production**

Use the Source-of-Truth Map above. Required corrections include:

- `moods` must no longer say "None currently" or that semantic mood normalization is deferred when current v2 production supplies/resolves moods.
- `lyrics_languages`, `artist_countries`, `artist_areas`, and `artist_languages` must describe current v2 behavior rather than v1 deferral language.
- Do not infer provider capability from old prose. Cross-check `providers/specs.py`, semantic provider code, mapping code, and tests. If a field is derived rather than directly emitted by a `ProviderSpec`, describe that accurately rather than inventing a provider row.
- Existing-library Item enrichment must be represented where production supports it.
- Ordinary `--apply` must include the authorized artwork sidecar/`Album.artpath` exception while still stating that audio files are unchanged without `--write`.
- Ordinary `--apply --write` must describe only supported prepared file synchronization and state that it performs no additional provider/analyzer work.
- `synced_lyrics` must retain its actual production limitation if it still has no lossless writable target; do not upgrade a preview/block-only field into a supported write path.
- Identity audit must remain independent of `providers.musicbrainz.enabled`.
- AcoustID must remain an existing-library evidence/identity feature; native beets/chroma owns importer acoustic matching/submission.
- Compatibility must remain Python `>=3.10,<3.15` and beets `>=2.12,<3` unless production metadata has changed; do not edit metadata during this docs task.

At the top of `technical-reference/index.md`, add a user-routing note equivalent to:

```markdown
Looking for setup instructions or examples? Start with **Configuration** or **Commands**. This section documents exact Noqlen Meta contracts and edge cases.
```

- [ ] **Step 5: Update the temporary MkDocs nav**

Replace top-level `Reference` with `Technical Reference` and point it to the moved files. Leave other old sections in place temporarily; later tasks replace them. Ensure every current Markdown page remains represented so the existing omitted-page check stays green.

- [ ] **Step 6: Run the exact-reference validation**

Run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/check_public_docs.py tests/docs/test_public_documentation.py mkdocs.yml site-docs/technical-reference
git add -u site-docs/reference
git commit -m "docs: establish verified technical reference"
```

---

### Task 2: Rebuild Home and Start Here as one continuous beginner journey

**Files:**
- Modify: `site-docs/index.md`
- Create: `site-docs/start-here/index.md`
- Create: `site-docs/start-here/installation.md`
- Create: `site-docs/start-here/basic-configuration.md`
- Create: `site-docs/start-here/first-preview.md`
- Create: `site-docs/start-here/understanding-results.md`
- Create: `site-docs/start-here/apply-changes.md`
- Create: `site-docs/start-here/write-files.md`
- Create: `site-docs/examples/starter-config.yaml`
- Delete: `site-docs/getting-started/index.md`
- Delete: `site-docs/getting-started/installation.md`
- Delete: `site-docs/getting-started/first-preview.md`
- Modify: `mkdocs.yml`
- Modify: `tests/docs/test_public_documentation.py`

**Interfaces:**
- Consumes: exact contracts from Technical Reference created in Task 1.
- Produces: the canonical beginner path used by later Configuration/Commands pages.

- [ ] **Step 1: Add tests for the continuous onboarding contract**

Add a test that checks the seven Start Here pages exist, the old directory is gone, and the continuous example is present in the operational pages:

```python
def test_start_here_is_a_continuous_existing_library_tutorial() -> None:
    start = ROOT / "site-docs" / "start-here"
    required = {
        "index.md",
        "installation.md",
        "basic-configuration.md",
        "first-preview.md",
        "understanding-results.md",
        "apply-changes.md",
        "write-files.md",
    }
    assert required == {path.name for path in start.glob("*.md")}
    assert not (ROOT / "site-docs" / "getting-started").exists()
    assert 'beet nm album:"Discovery"' in (start / "first-preview.md").read_text()
    assert 'beet nm --apply album:"Discovery"' in (start / "apply-changes.md").read_text()
    assert 'beet nm --apply --write album:"Discovery"' in (start / "write-files.md").read_text()
```

Run the new test and confirm it fails before migration.

- [ ] **Step 2: Rewrite the Home page as a product entry point**

`site-docs/index.md` must answer, in this order:

1. What Noqlen Meta is.
2. What it can enrich: release/track/artist metadata, genres/styles/moods, artwork, optional local BPM, lyrics/languages, identity/AcoustID workflows.
3. Safety: preview is the default and non-mutating.
4. Primary CTA to Start Here; secondary CTA to Configuration.
5. Compact project links for PyPI, GitHub, license, and release information below the onboarding content.

Keep factual release statements currently required by `scripts/check_public_docs.py`/release tests, but do not make release status the visual/semantic focus.

- [ ] **Step 3: Write Start Here pages with the exact continuous flow**

Use `Discovery` consistently as a teaching target; explicitly say it is only an example and can be replaced with the reader's album.

`start-here/index.md`:
- plain-language product explanation;
- beets relationship;
- preview safety;
- what the tutorial will accomplish;
- no internal type names or architecture terms.

`start-here/installation.md`:

```bash
pip install beets-noqlenmeta
beet config -p
```

Then:

```yaml
plugins:
  - noqlenmeta
```

Verification:

```bash
beet nm --help
```

Keep `BEETSDIR`, alternate config files, plugin discovery internals, and unusual environments out of the normal path; link to Troubleshooting/Technical Reference instead.

`start-here/basic-configuration.md` must teach this starter shape and explain each block in plain language:

```yaml
noqlenmeta:
  providers:
    musicbrainz:
      enabled: true
    coverartarchive:
      enabled: true

  fields:
    genres: true
    styles: true
    moods: true
    cover: true

  genres:
    num_genres: 1

  moods:
    max_moods: 1
```

`start-here/first-preview.md`:

```bash
beet nm album:"Discovery"
```

Explain `album:"Discovery"` as a beets query selecting an album by its album field. Do not teach the whole query language here.

`start-here/understanding-results.md`:
- `KEEP`: current value retained;
- `PROPOSE`: Noqlen has a safe-enough prepared value, but preview changed nothing;
- `REVIEW`: useful evidence exists but automatic safety/confidence is insufficient;
- `BLOCKED`: a safety/identity/mapping/contract rule prevented the change.

`start-here/apply-changes.md`:

```bash
beet nm --apply album:"Discovery"
```

Explain database application and the v2 artwork-sidecar exception. Introduce database vs audio-file tags here, not earlier.

`start-here/write-files.md`:

```bash
beet nm --apply --write album:"Discovery"
```

Explain supported prepared file synchronization and explicitly state that adding `--write` does not perform another provider lookup or analyzer pass.

End with the mental model:

```text
configure -> preview -> review -> apply -> write, when wanted
```

Then route the reader to Configuration or Recipes -> Enrich During Import.

- [ ] **Step 4: Create a copyable starter YAML example**

Create `site-docs/examples/starter-config.yaml` containing both plugin enablement and the starter `noqlenmeta` block shown above. It is a documentation example only; it must not alter defaults or introduce a runtime preset.

- [ ] **Step 5: Remove the old Getting Started directory and update nav**

Use `git rm` for the old three pages. In `mkdocs.yml`, replace `Getting Started` with `Start Here`, using the seven pages in tutorial order. Keep remaining legacy sections temporarily.

- [ ] **Step 6: Validate**

Run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add site-docs/index.md site-docs/start-here site-docs/examples/starter-config.yaml mkdocs.yml tests/docs/test_public_documentation.py
git add -u site-docs/getting-started
git commit -m "docs: rebuild beginner onboarding"
```

---

### Task 3: Create the friendly Configuration section

**Files:**
- Create: `site-docs/configuration/index.md`
- Create: `site-docs/configuration/fields.md`
- Create: `site-docs/configuration/providers.md`
- Create: `site-docs/configuration/genres-styles.md`
- Create: `site-docs/configuration/moods.md`
- Create: `site-docs/configuration/artwork.md`
- Create: `site-docs/configuration/bpm.md`
- Create: `site-docs/configuration/lyrics-languages.md`
- Create: `site-docs/configuration/acoustid.md`
- Create: `site-docs/configuration/advanced-resolution.md`
- Create: `site-docs/configuration/full-example.md`
- Modify: `scripts/check_public_docs.py`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `mkdocs.yml`

**Interfaces:**
- Consumes: `default_config()`, Technical Reference, provider capability/source code.
- Produces: human-oriented configuration documentation; no dotted-path completeness requirement is moved out of Technical Reference.

- [ ] **Step 1: Add configuration-section structure tests**

Add a test asserting all eleven pages exist and that `moods.md` teaches both the permission switch and the limiter:

```python
def test_friendly_configuration_covers_mood_relationship() -> None:
    page = (ROOT / "site-docs/configuration/moods.md").read_text(encoding="utf-8")
    assert "fields:" in page
    assert "moods: true" in page
    assert "max_moods: 1" in page
    assert "max_moods: 3" in page
```

Also add a validator rule that `site-docs/configuration/full-example.md` contains the exact `full-config.yaml` text inside a YAML fence, so the displayed full example cannot silently drift from the machine-checked default file. Implement this by reading the full YAML file and checking for:

```python
expected_block = f"```yaml\n{full_config_text.strip()}\n```"
```

Do not add prose-string assertions beyond structural/factual examples.

Run targeted tests and confirm the new page tests fail before creation.

- [ ] **Step 2: Write Configuration Overview**

`configuration/index.md` shows only the major shape:

```yaml
noqlenmeta:
  fields:
    ...
  providers:
    ...
  genres:
    ...
  moods:
    ...
  artwork:
    ...
  bpm:
    ...
  local_analysis:
    ...
  acoustid:
    ...
  resolution:
    ...
```

Explain each block in one or two sentences. State that `resolution` is advanced and most users can leave it alone.

- [ ] **Step 3: Write Fields and Providers around user intent**

`configuration/fields.md` starts with a realistic partial YAML and explains that fields choose which metadata Noqlen may handle. Group release/album, track, artist, and artwork fields. Every public `fields.*` leaf from `default_config()` must be mentioned in the friendly page or linked to its relevant topic page; exact target/storage details remain in Technical Reference.

Do not claim `synced_lyrics` is writable if production still blocks it due to no lossless target. Do not advertise local mood analysis as a working feature merely because `local_analysis.mood.enabled` exists in defaults.

`configuration/providers.md` explains practical use before matrices:
- MusicBrainz: default release/track/artist semantic source where current production supports it; no API key requirement.
- Cover Art Archive: cover source; no API key requirement.
- Discogs: release metadata including genres/styles/labels/catalog/barcode/country/year/media/format information; document current token/dependency requirement exactly.
- Last.fm: current release/track/artist genres/styles/moods capabilities from `providers/specs.py`; document actual credential/network requirements from code.
- iTunes: current release genres/year role and storefront setting; never describe storefront as release country.
- LRCLIB: track lyrics/synced-lyrics source; explain the separate writable-target limitation for synced lyrics.

Show relevant field + provider combinations together.

- [ ] **Step 4: Write feature pages using the mandatory editorial order**

Every feature page uses: what it does -> minimal YAML -> plain explanation -> default -> useful alternatives -> important interactions -> Technical Reference link.

`genres-styles.md`:
- explain `fields.genres`, `fields.styles`, `genres.num_genres`, `genres.promote_styles`;
- explain styles remain lossless/multivalued while promoted recognized styles may inform genre resolution;
- do not imply hidden parent-genre padding.

`moods.md` must include:

```yaml
fields:
  moods: true

moods:
  max_moods: 1
```

and:

```yaml
moods:
  max_moods: 3
```

Plain-language contract: the number is a maximum; Noqlen may keep up to that many independently supported canonical moods and does not invent/pad values to reach it. State default `1` and allowed range `1..10` only if current production validation/reference confirms that range.

`artwork.md`:
- `fields.cover` + `providers.coverartarchive.enabled`;
- `artwork.size` accepted current values;
- `replace_existing` behavior;
- fixed `cover.jpg`, `Album.artpath`, multidisc behavior, and optional embedding with correct mutation boundaries.

`bpm.md` must distinguish:

```yaml
fields:
  bpm: true
```

from:

```yaml
local_analysis:
  bpm:
    enabled: true
```

Explain `[audio]` installation, current local backend, preservation/recalculation, rounding, analysis mode/window, and octave normalization from production. Do not imply an external BPM provider exists.

`lyrics-languages.md`:
- plain lyrics and synced lyrics as separate fields;
- LRCLIB provider relationship;
- current lyrics-language metadata;
- current artist country/area/language behavior;
- accurately preserve any writable-target limitations.

`acoustid.md`:
- existing-library identity/evidence purpose;
- enablement, fingerprint reuse, optional missing fingerprint computation, lookup, score/margin/result bounds, timeout/rate/cache/fpcalc settings;
- API key environment requirement where current lookup requires it;
- relationship to `--identity` when `use_for_identity` is enabled;
- explicit statement that native beets/chroma owns importer acoustic matching/submission.

`advanced-resolution.md`:
- lead with "most users do not need this";
- explain `authority`, `min_confidence`, `preserve_existing` through concrete examples;
- exact mapping/validation rules link to Technical Reference.

- [ ] **Step 5: Write the Full Configuration Example page from the machine-checked YAML**

`configuration/full-example.md` must state:

> This is a reference example, not a recommended starter configuration.

Then include the complete contents of `site-docs/examples/full-config.yaml` in one YAML fence. Do not edit production defaults merely to make this page simpler.

- [ ] **Step 6: Add Configuration to MkDocs nav**

Place it immediately after Start Here in the approved order. Keep legacy Concepts/Guides temporarily.

- [ ] **Step 7: Validate**

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add site-docs/configuration mkdocs.yml scripts/check_public_docs.py tests/docs/test_public_documentation.py
git commit -m "docs: add beginner configuration guide"
```

---

### Task 4: Create goal-oriented Commands pages

**Files:**
- Create: `site-docs/commands/index.md`
- Create: `site-docs/commands/preview.md`
- Create: `site-docs/commands/apply.md`
- Create: `site-docs/commands/write-files.md`
- Create: `site-docs/commands/whole-library.md`
- Create: `site-docs/commands/identity.md`
- Create: `site-docs/commands/acoustid.md`
- Create: `site-docs/commands/identity-tags.md`
- Modify: `mkdocs.yml`
- Modify: `tests/docs/test_public_documentation.py`

**Interfaces:**
- Consumes: exact CLI matrix from `technical-reference/command-line.md` and `NoqlenMetaPlugin().commands()[0]`.
- Produces: task-oriented command docs; Technical Reference remains canonical for every option/combination.

- [ ] **Step 1: Add command-flow tests**

Add a factual test for the main user-facing examples:

```python
def test_command_guides_cover_core_user_goals() -> None:
    docs = ROOT / "site-docs" / "commands"
    assert "beet nm QUERY" in (docs / "preview.md").read_text()
    assert "beet nm --apply QUERY" in (docs / "apply.md").read_text()
    assert "beet nm --apply --write QUERY" in (docs / "write-files.md").read_text()
    assert "beet nm --all" in (docs / "whole-library.md").read_text()
    assert "beet nm --identity QUERY" in (docs / "identity.md").read_text()
    assert "beet nm --acoustid QUERY" in (docs / "acoustid.md").read_text()
```

Run and confirm failure before creation.

- [ ] **Step 2: Write Command Overview**

`commands/index.md` starts with this intent map:

```text
See what Noqlen would change -> beet nm QUERY
Save approved changes -> beet nm --apply QUERY
Also synchronize supported tags to files -> beet nm --apply --write QUERY
Process the whole library -> beet nm --all
Repair MusicBrainz identity -> beet nm --identity QUERY
Use acoustic fingerprints/evidence -> beet nm --acoustid QUERY
```

Explain that exact flags, invalid combinations, and edge cases live in Technical Reference.

- [ ] **Step 3: Write ordinary-enrichment command pages**

`preview.md`: default non-mutating mode, narrow query examples, minimal beets-query explanation and links.

`apply.md`: `--apply` ordinary database authority plus authorized artwork sidecar/`Album.artpath`; no audio-file mutation.

`write-files.md`: `--apply --write`, supported prepared metadata synchronization, optional prepared artwork embedding where production permits it, and the non-expansion rule: `--write` does not trigger new provider/analyzer work.

`whole-library.md`:

```bash
beet nm --all
beet nm --all --apply
beet nm --all --apply --write
```

Recommend testing a narrow album/artist query first without portraying Noqlen as unsafe.

- [ ] **Step 4: Write identity/AcoustID/identity-tag pages as separate goals**

`identity.md`: audit/repair MusicBrainz identity; keep its preview/apply authority separate from ordinary enrichment; explicitly state `providers.musicbrainz.enabled` neither enables nor disables identity audit.

`acoustid.md`: existing-library fingerprint/evidence command semantics; reuse existing fingerprint when allowed; optional compute-missing behavior; lookup and identity filtering; no importer acoustic ownership.

`identity-tags.md`: the specialized coherent four-MBID file-tag synchronization path and its own preview/write authority. Do not make it sound like ordinary `--apply --write`.

- [ ] **Step 5: Add Commands to MkDocs nav and validate**

Place after Configuration. Then run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add site-docs/commands mkdocs.yml tests/docs/test_public_documentation.py
git commit -m "docs: organize commands by user goal"
```

---

### Task 5: Replace old How-to Guides with complete Recipes

**Files:**
- Create: `site-docs/recipes/index.md`
- Create: `site-docs/recipes/existing-library.md`
- Create: `site-docs/recipes/import-enrichment.md`
- Create: `site-docs/recipes/artwork.md`
- Create: `site-docs/recipes/local-bpm.md`
- Create: `site-docs/recipes/lyrics-languages.md`
- Create: `site-docs/recipes/repair-musicbrainz-ids.md`
- Create: `site-docs/recipes/whole-library.md`
- Delete: all Markdown under `site-docs/guides/`
- Modify: `mkdocs.yml`
- Modify: `tests/docs/test_public_documentation.py`

**Interfaces:**
- Consumes: Start Here, Configuration, Commands, Technical Reference.
- Produces: complete goal recipes without duplicating exact contract tables.

- [ ] **Step 1: Add recipe coverage test**

Assert the seven required recipe pages plus index exist and old `guides/` is gone. Run the test and confirm failure.

- [ ] **Step 2: Write Existing Library and Import recipes**

`existing-library.md` must be a complete progression:
1. choose fields/providers;
2. preview one album;
3. inspect statuses;
4. apply;
5. optionally write files;
6. scale to a larger query or `--all`.

Correct the stale old guide: ordinary mode can process current production album and singleton Item targets; do not say library mode is Album-only or that LRCLIB is never called for track-only Items if production supports it.

`import-enrichment.md` is the secondary onboarding path. Explain importer integration only after the ordinary workflow. Remove v1-only wording that calls shipped v2 semantic capabilities deferred/mapping-blocked. Preserve actual importer limitations and make clear that native beets/chroma owns importer acoustic matching.

- [ ] **Step 3: Write feature recipes with only relevant configuration**

`artwork.md` combines `fields.cover`, CAA enablement, artwork size/replace policy, preview/apply/write behavior, `cover.jpg`, artpath, and embedding boundaries.

`local-bpm.md` begins with:

```bash
pip install "beets-noqlenmeta[audio]"
```

then shows `fields.bpm` plus `local_analysis.bpm.enabled`, followed by a real preview/apply command. Explain preservation and optional recalculation.

`lyrics-languages.md` shows exact current field/provider combinations for plain lyrics and semantic language metadata. Keep synced-lyrics target limitations explicit.

`repair-musicbrainz-ids.md` uses identity workflow only; do not route through ordinary semantic MusicBrainz provider settings.

`whole-library.md` uses preview -> inspect -> apply -> optional write. Add a short "after file writes" note explaining that external library scanners such as Navidrome may need their own rescan and Noqlen does not call a Navidrome API. This absorbs the still-useful part of the old standalone Navidrome guide without keeping a redundant top-level recipe.

- [ ] **Step 4: Remove legacy Guides and update nav**

Delete `site-docs/guides/` after its accurate material has been migrated. Replace `How-to Guides` with `Recipes` in MkDocs.

- [ ] **Step 5: Validate**

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add site-docs/recipes mkdocs.yml tests/docs/test_public_documentation.py
git add -u site-docs/guides
git commit -m "docs: replace guides with task recipes"
```

---

### Task 6: Split Troubleshooting by user-visible symptom

**Files:**
- Rewrite: `site-docs/troubleshooting/index.md`
- Create: `site-docs/troubleshooting/nothing-changed.md`
- Create: `site-docs/troubleshooting/review-blocked.md`
- Create: `site-docs/troubleshooting/providers.md`
- Create: `site-docs/troubleshooting/file-writing.md`
- Create: `site-docs/troubleshooting/acoustid.md`
- Modify: `mkdocs.yml`
- Modify: `tests/docs/test_public_documentation.py`

**Interfaces:**
- Consumes: exact status/provider/write/AcoustID contracts.
- Produces: symptom-first diagnostics; canonical conceptual explanations remain in Advanced/Technical Reference.

- [ ] **Step 1: Add troubleshooting structure test**

Assert all six pages exist and the index links to each symptom page. Confirm failure before creation.

- [ ] **Step 2: Rewrite Common Problems index**

Keep it short: choose a symptom and route to the dedicated page. Do not retain the current mega-page structure.

- [ ] **Step 3: Write Nothing Was Changed**

Diagnose in this exact practical order:
1. relevant field enabled;
2. appropriate provider/source enabled and usable;
3. enough identity/evidence exists;
4. existing-value preservation prevents replacement;
5. result is `REVIEW`/`BLOCKED`;
6. beets query selected the intended items.

Each step contains a concrete config or command check.

- [ ] **Step 4: Write REVIEW/BLOCKED, Provider, File Writing, and AcoustID troubleshooting**

`review-blocked.md`: operational meaning first, common causes, safe next steps, links to Advanced exact concepts. Never suggest a force mode; none exists.

`providers.md`: credentials/dependencies, identity prerequisites, network behavior, scope, and provider/field mismatch symptoms. Base claims on provider code/specs.

`file-writing.md`: database-vs-file expectations; `--apply` vs `--apply --write`; supported tag targets; cover sidecar vs embedded art; file permissions; relevant native beets interactions.

`acoustid.md`: reuse existing fingerprints, `fpcalc`, compute-missing, API key when lookup requires it, thresholds/margins, bounded results, and identity filtering.

- [ ] **Step 5: Update nav and validate**

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add site-docs/troubleshooting mkdocs.yml tests/docs/test_public_documentation.py
git commit -m "docs: make troubleshooting symptom oriented"
```

---

### Task 7: Migrate Concepts into Advanced and remove the legacy concept hierarchy

**Files:**
- Create: `site-docs/advanced/index.md`
- Create/rewrite: `site-docs/advanced/database-vs-file-tags.md`
- Create/rewrite: `site-docs/advanced/preview-apply-write.md`
- Create/rewrite: `site-docs/advanced/strict-vs-partial.md`
- Create/rewrite: `site-docs/advanced/provider-authority-resolution.md`
- Audit/rewrite: `site-docs/advanced/safety.md`
- Audit/rewrite: `site-docs/advanced/architecture.md`
- Delete: all Markdown under `site-docs/concepts/`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `mkdocs.yml`

**Interfaces:**
- Consumes: useful conceptual material from old `concepts/` and current advanced pages, corrected against v2 runtime.
- Produces: canonical mental-model explanations for database/files, preview/apply/write, strict/partial, provider authority, safety, architecture, and result statuses where contextually needed.

- [ ] **Step 1: Update the release/documentation test path before deleting Concepts**

`tests/docs/test_public_documentation.py::test_public_release_state_is_consistent` currently reads `site-docs/concepts/preview-apply-write.md`. Change it to read:

```python
permissions = (ROOT / "site-docs/advanced/preview-apply-write.md").read_text(
    encoding="utf-8"
)
```

Add a structure assertion that `site-docs/concepts` is absent at completion. Run the relevant test; expect failure until the new advanced file exists.

- [ ] **Step 2: Write Database vs File Tags**

Use accurate material from `concepts/database-files-navidrome.md` but correct it for v2 ordinary `--apply --write`. Explain:
- beets database values;
- tags inside audio files;
- artwork sidecars/artpath as a distinct non-audio-file write under authorized `--apply`;
- external scanners such as Navidrome observe file/database changes only according to their own rescan behavior; Noqlen does not control their API/cache.

- [ ] **Step 3: Write Preview, Apply and Write as the canonical conceptual model**

Migrate/correct `concepts/preview-apply-write.md` and result-status concepts. Required factual wording remains discoverable for existing tests/validator:
- verified `cover.jpg` sidecars may be written under authorized ordinary apply;
- audio files remain unchanged unless `--write`;
- adding `--write` never triggers another provider call or analyzer expansion;
- preview is non-mutating;
- identity/AcoustID/identity-tags have separate authorities;
- native `beet write` and `import.write` are separate beets controls, not aliases of Noqlen `--write`.

Explain `KEEP`, `PROPOSE`, `REVIEW`, `BLOCKED` here at conceptual depth; Troubleshooting remains the practical symptom page.

- [ ] **Step 4: Write Strict vs Partial and Provider Authority/Resolution**

`strict-vs-partial.md`: preserve the exact guarantee that partial is not force. Explain how partial withholds unsafe/unmappable fields while allowing independently safe work; it does not bypass evidence or identity rules.

`provider-authority-resolution.md`: explain candidate providers, field authority, confidence, preservation, and why order/thresholds exist. Link to Configuration -> Advanced Resolution for examples and Technical Reference for exact paths.

- [ ] **Step 5: Audit Safety and Architecture**

`advanced/safety.md` must reflect current v2 mutation boundaries, verified prepared-plan application, artwork separation, preview default, no force mode, and no extra provider work from `--write`.

`advanced/architecture.md` may retain internal conceptual names only because this is Advanced, but remove stale v1-only behavior. Do not require architecture knowledge anywhere in Start Here/Configuration/Commands.

- [ ] **Step 6: Delete old Concepts, finalize Advanced nav, and validate**

Delete `site-docs/concepts/`. Update MkDocs so `Concepts` no longer exists top-level and Advanced uses the approved order.

Run:

```bash
pytest tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add site-docs/advanced mkdocs.yml tests/docs/test_public_documentation.py
git add -u site-docs/concepts
git commit -m "docs: move concepts into advanced guidance"
```

---

### Task 8: Final stale-content audit, exact navigation lock, and repository verification

**Files:**
- Modify as needed: `site-docs/**/*.md`
- Modify as needed: `mkdocs.yml`
- Modify as needed: `scripts/check_public_docs.py`
- Modify as needed: `tests/docs/test_public_documentation.py`
- Modify only if required by truthful release-state wording: `site-docs/project/release.md`, `site-docs/project/changelog.md`, `README.md`, `tests/release/test_release_contracts.py`
- Do not modify runtime package files.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: final review-ready branch for ChatGPT/GitHub inspection and PR/CI; OpenCode must not merge it.

- [ ] **Step 1: Lock the final top-level navigation in a structural test**

Add a test that loads `mkdocs.yml` and asserts the top-level labels are exactly:

```python
[
    "Home",
    "Start Here",
    "Configuration",
    "Commands",
    "Recipes",
    "Troubleshooting",
    "Technical Reference",
    "Advanced",
    "Project",
]
```

The test may inspect YAML structure rather than prose. It should also assert the old directories `getting-started`, `concepts`, `guides`, and `reference` are absent.

- [ ] **Step 2: Set the final MkDocs nav**

Use this order:

```text
Home
Start Here
  What is Noqlen Meta?
  Installation
  Basic Configuration
  Your First Preview
  Understanding the Results
  Apply Your First Changes
  Write Changes to Your Files
Configuration
  Configuration Overview
  Fields
  Providers
  Genres & Styles
  Moods
  Artwork
  BPM
  Lyrics & Languages
  AcoustID
  Advanced Resolution
  Full Configuration Example
Commands
  Command Overview
  Preview Metadata
  Apply Metadata
  Write Metadata to Files
  Process the Whole Library
  Repair MusicBrainz Identity
  Use AcoustID
  Sync Identity Tags
Recipes
  Enrich an Existing Library
  Enrich During Import
  Add or Replace Album Covers
  Analyze BPM Locally
  Add Lyrics and Language Metadata
  Repair MusicBrainz IDs
  Safely Update an Entire Library
Troubleshooting
  Common Problems
  Nothing Was Changed
  REVIEW and BLOCKED Results
  Provider Problems
  File Writing Problems
  AcoustID Problems
Technical Reference
  Configuration Reference
  Command-line Reference
  Fields Reference
  Providers Reference
  beets Interaction
  Compatibility
Advanced
  Database vs File Tags
  Preview, Apply and Write
  Strict vs Partial
  Provider Authority and Resolution
  Safety Guarantees
  Architecture
Project
  Changelog
  Contributing
  Release
```

Use navigation indexes where appropriate, but do not introduce extra user-facing categories.

- [ ] **Step 3: Run targeted stale-v1 searches and manually classify every hit**

Run:

```bash
grep -RniE "None currently|deferred|v1 blocks|Album-only|database-only|noqlen-meta-plugin\.readthedocs\.io|repository release candidate|currently published release:.*1\.0\.0" site-docs README.md || true
grep -RniE "FieldDecision|ChangePlan|BeetsTargetPlan|TrackTargetPlan|docs/context/|docs/specs/|docs/adr/|handoff\.md" site-docs README.md || true
```

For every hit:
- historical v1 text in changelog/release history may remain only when clearly historical and factually correct;
- current-user documentation must not present shipped v2 capabilities as deferred/unavailable;
- internal project material must not be linked from public docs;
- obsolete RTD hostname must not remain.

Do not remove legitimate v1 release history merely because it contains `v1`.

- [ ] **Step 4: Verify friendly docs against exact reference and production**

Perform a manual cross-check for these high-risk topics:
- moods and `max_moods`;
- lyrics, synced lyrics, lyrics languages;
- artist country/area/languages;
- existing-library singleton Items;
- `--apply` artwork sidecar boundary;
- `--apply --write` file-sync boundary;
- provider scopes/credentials;
- local BPM and no external BPM provider;
- identity separation from semantic MusicBrainz provider;
- AcoustID existing-library role and native beets/chroma importer ownership.

If documentation and code disagree, correct documentation. If code/tests themselves disagree, stop and report rather than silently choosing one.

- [ ] **Step 5: Run the full local verification gate**

Run in this order:

```bash
ruff check .
pytest tests/docs/test_public_documentation.py -q
pytest tests/release/test_release_contracts.py -q
python scripts/check_public_docs.py
mkdocs build --strict
pytest -m "not live"
python scripts/check_repo_contamination.py
```

Expected: every command exits 0.

Then inspect:

```bash
git status --short
git diff main...HEAD --stat
git diff main...HEAD -- beetsplug/noqlenmeta
```

Expected for the runtime diff command: no output. Documentation redesign must not alter package runtime files.

- [ ] **Step 6: Commit final audit fixes**

If Step 3-5 required changes:

```bash
git add site-docs mkdocs.yml scripts/check_public_docs.py tests/docs/test_public_documentation.py README.md tests/release/test_release_contracts.py
git commit -m "docs: complete documentation v2 migration"
```

If there are no final changes, do not create an empty commit.

- [ ] **Step 7: Produce the OpenCode handoff report and stop before merge**

Report exactly:
- branch name;
- final HEAD SHA;
- commits created by Tasks 1-8;
- deleted legacy directories;
- all verification commands and their exit status;
- any factual ambiguity discovered and how it was resolved;
- `git diff main...HEAD --stat` summary;
- confirmation that `git diff main...HEAD -- beetsplug/noqlenmeta` is empty.

Do not open/merge a PR as part of the heavy executor handoff unless explicitly instructed later. Return control to ChatGPT/GitHub review for diff inspection, CI, corrections, and merge authorization.

## OpenCode Execution Boundary

Use this plan as the bounded OpenCode task contract. OpenCode may make editorial wording choices within the approved page purposes, but it may not redesign the information architecture, add product features, weaken validation, reinterpret runtime behavior, retag releases, or merge to `main`.

If a page requires a factual decision that cannot be resolved from the Source-of-Truth Map and existing tests, OpenCode must stop on that item and report the ambiguity instead of guessing.
