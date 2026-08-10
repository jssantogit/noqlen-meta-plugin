# Noqlen Meta v2 Genre Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, Noqlen-owned genre-classification foundation that is independent of beets LastGenre, promotes recognized Discogs styles, combines provider evidence, and returns one specific genre by default.

**Architecture:** Keep ordinary metadata resolution generic. Add a small genre-specific pipeline before `resolve_metadata()`: current provider candidates become normalized `GenreEvidence`, a pure `GenreResolver` selects canonical genres using packaged taxonomy and deterministic evidence rules, and one aggregate genre `FieldDecision` rejoins the existing `build_change_plan()` path. The Foundation uses only provider data already collected today; new MusicBrainz `inc=genres`, Last.fm track/artist collection, and other online evidence work remain Semantic Enrichment.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, standard-library `importlib.resources`/`urllib`, pytest, Ruff, setuptools package data.

## Global Constraints

- Python support remains `>=3.10,<3.15`.
- Runtime dependency floor remains `beets>=2.12,<3`; add no new runtime dependency.
- The base plugin remains usable without another beets plugin.
- Runtime genre classification must not import `beetsplug.lastgenre`, read its `genres.txt`, or require LastGenre to be installed/enabled.
- Runtime taxonomy lookup is local and deterministic; no taxonomy network refresh occurs during ordinary plugin execution.
- `fields.genres` remains the field enable/disable switch. The `genres` configuration section only tunes classification.
- Default `genres.num_genres` is `1`; accepted range is `1..10`.
- Default `genres.promote_styles` is `true`.
- Do not automatically insert broad parent genres.
- A Discogs style may contribute genre evidence only when the Noqlen taxonomy recognizes it as a genre; the same value remains preserved in `styles`.
- Reliable genre scope preference is `TRACK > RELEASE > ARTIST`; weak evidence is filtered before scope preference.
- Consensus counts distinct providers, not evidence rows.
- Do not expose arithmetic provider scores/weights as public configuration.
- Do not create/register a fake `noqlen-genre` provider.
- Existing user genres remain governed by the ordinary `preserve_existing` policy.
- Existing database/file-sync `genres` persistence and `--apply`/`--write` authority remain unchanged.
- No real user music library is used in tests.
- Do not implement new MusicBrainz genre network calls, new Last.fm track/artist calls, mood taxonomy, or version/release changes in this plan.

---

## File Structure

### Packaged taxonomy

- Create `beetsplug/noqlenmeta/genre_taxonomy/__init__.py` — load/cache packaged vocabulary, canonicalize labels, classify semantic/noise categories, expose taxonomy snapshot ID.
- Create `beetsplug/noqlenmeta/genre_taxonomy/aliases.py` — small reviewed aliases, broad categories, mood/origin/descriptor/noise constants only.
- Create `beetsplug/noqlenmeta/genre_taxonomy/genres.txt` — complete reviewed snapshot generated from MusicBrainz `/ws/2/genre/all?fmt=txt`.
- Create `scripts/update_genre_taxonomy.py` — development-only bounded fetch/update helper; no runtime use.
- Modify `pyproject.toml` — include `genres.txt` in wheel/sdist package data.
- Create `tests/test_genre_taxonomy.py`.

### Evidence and resolver

- Create `beetsplug/noqlenmeta/genre_evidence.py` — immutable `GenreEvidenceKind` and `GenreEvidence` facts.
- Create `beetsplug/noqlenmeta/genre_resolution.py` — `GenreSettings`, evidence dedupe/profile ordering, pure `resolve_genres()`.
- Create `tests/test_genre_resolution.py`.

### Existing-candidate integration

- Create `beetsplug/noqlenmeta/genre_pipeline.py` — convert already-collected `MetadataCandidate` values to release-scope genre evidence, promote recognized styles, create the aggregate genre `FieldDecision`, retain concise evidence provenance.
- Modify `beetsplug/noqlenmeta/__init__.py` — route release genre candidates through the specialized pipeline before the generic resolver for both importer and existing-library release paths.
- Modify `beetsplug/noqlenmeta/resolver.py` — make MusicBrainz an allowed future genre authority but keep generic resolution provider-agnostic; do not add genre special cases here.
- Create `tests/test_genre_pipeline.py`.
- Modify `tests/test_v2_foundation_command.py` only for command-level behavior that cannot be proven in pure tests.

### Current Last.fm decoupling

- Modify `beetsplug/noqlenmeta/providers/lastfm.py` — replace `load_beets_genre_vocabulary()`/LastGenre resource discovery with the packaged Noqlen taxonomy while preserving the current album-only network contract for now.
- Modify `tests/test_lastfm_provider.py` — prove operation with LastGenre unavailable and preserve current identity/weight/max-tag safeguards.

### Config and documentation

- Modify `beetsplug/noqlenmeta/configuration.py` — add `genres.num_genres=1` and `genres.promote_styles=true`.
- Modify `site-docs/reference/configuration.md` — document only the two public genre tuning settings and their semantics.
- Modify `site-docs/reference/fields.md` — describe `genres` as Noqlen-resolved classification and `styles` as preserved source style metadata.
- Modify `site-docs/examples/full-config.yaml` — show defaults.
- Modify `tests/docs/test_public_documentation.py` where needed for the public config contract.

---

### Task 1: Package a Noqlen-owned genre taxonomy and semantic classifier

**Files:**
- Create: `beetsplug/noqlenmeta/genre_taxonomy/__init__.py`
- Create: `beetsplug/noqlenmeta/genre_taxonomy/aliases.py`
- Create: `beetsplug/noqlenmeta/genre_taxonomy/genres.txt`
- Create: `scripts/update_genre_taxonomy.py`
- Modify: `pyproject.toml`
- Test: `tests/test_genre_taxonomy.py`

**Interfaces:**
- Produces: `GenreSemanticCategory` enum with `GENRE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, `NOISE`, `UNKNOWN`.
- Produces: `GenreClassification(canonical_name: str, category: GenreSemanticCategory, broad: bool)`.
- Produces: `GenreTaxonomy.classify(raw: str, *, artist_names: tuple[str, ...] = ()) -> GenreClassification`.
- Produces: `GenreTaxonomy.is_genre(raw: str) -> bool`.
- Produces: `GenreTaxonomy.snapshot_id: str`, computed deterministically from packaged `genres.txt` bytes.
- Produces: `DEFAULT_GENRE_TAXONOMY` loaded only from package resources.
- Development script source: MusicBrainz `/ws/2/genre/all?fmt=txt`, which officially returns all genre names newline-separated and alphabetically ordered.

- [ ] **Step 1: Write failing taxonomy tests**

Create tests equivalent to:

```python
from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)


def test_taxonomy_recognizes_representative_specific_genres() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    for value in (
        "K-pop",
        "technical death metal",
        "progressive metal",
        "melodic death metal",
        "drum and bass",
    ):
        result = taxonomy.classify(value)
        assert result.category is GenreSemanticCategory.GENRE
        assert result.canonical_name


def test_aliases_collapse_to_one_canonical_identity() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    assert taxonomy.classify("kpop").canonical_name == taxonomy.classify("K-Pop").canonical_name
    assert taxonomy.classify("rnb").canonical_name == taxonomy.classify("R&B").canonical_name
    assert taxonomy.classify("dnb").canonical_name == taxonomy.classify("drum and bass").canonical_name


def test_classifier_separates_non_genre_semantics() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    assert taxonomy.classify("Energetic").category is GenreSemanticCategory.MOOD
    assert taxonomy.classify("Korean").category is GenreSemanticCategory.ORIGIN
    assert taxonomy.classify("Girl Group").category is GenreSemanticCategory.DESCRIPTOR
    assert taxonomy.classify("2024").category is GenreSemanticCategory.NOISE
    assert taxonomy.classify("Spotify").category is GenreSemanticCategory.NOISE
    assert taxonomy.classify("Synthetic Artist", artist_names=("Synthetic Artist",)).category is GenreSemanticCategory.NOISE
```

Also assert `Rock`, `Pop`, `Metal`, and `Electronic` are marked broad while `Technical Death Metal`, `K-pop`, and `Drum and Bass` are not.

- [ ] **Step 2: Run taxonomy tests and verify failure**

```bash
pytest tests/test_genre_taxonomy.py -q
```

Expected: FAIL because the taxonomy package does not exist.

- [ ] **Step 3: Add aliases and semantic constants**

In `aliases.py`, keep the curated layer intentionally small. Include at least canonical mappings for:

```python
ALIASES = {
    "kpop": "K-pop",
    "k-pop": "K-pop",
    "rnb": "R&B",
    "r&b": "R&B",
    "dnb": "Drum and Bass",
    "drum n bass": "Drum and Bass",
    "drum & bass": "Drum and Bass",
}
```

Use the exact canonical spelling that exists in the generated taxonomy; if upstream spelling differs, point aliases to that spelling rather than creating a duplicate identity.

Define a deliberately small broad set, not a hierarchy:

```python
BROAD_GENRES = frozenset({
    "Blues", "Classical", "Country", "Electronic", "Folk", "Hip Hop",
    "Jazz", "Latin", "Metal", "Pop", "R&B", "Reggae", "Rock",
})
```

Define small semantic sets/patterns sufficient to reject known Last.fm contamination without pretending to solve the future mood system: representative moods (`Energetic`, `Aggressive`, `Dreamy`, `Melancholic`, `Atmospheric`, `Dark`, `Happy`, `Sad`, `Chill`), origin descriptor `Korean`, descriptor `Girl Group`, and deterministic noise rules for year/decade, personal/favorite terms, platforms, Last.fm meta terms, generic `song`/`track`/`album`/`vocal`, same-as-artist, and obvious long personal phrases.

- [ ] **Step 4: Implement the pure packaged taxonomy loader/classifier**

Use `importlib.resources.files(__package__).joinpath("genres.txt").read_text(encoding="utf-8")`. Normalize lookup keys with Unicode NFKC, whitespace collapse, and `casefold()`. Preserve the canonical spelling from `genres.txt` in returned classifications.

`GenreTaxonomy` must validate that the snapshot is non-empty and contains no casefold duplicates. `snapshot_id` is the first 16 hexadecimal characters of SHA-256 over the exact packaged `genres.txt` UTF-8 bytes; do not hardcode a mutable date string.

Classification order must be deterministic:

```text
empty -> UNKNOWN
same-as-artist / structural noise -> NOISE
known mood -> MOOD
known origin -> ORIGIN
known descriptor -> DESCRIPTOR
alias/canonical taxonomy match -> GENRE
otherwise -> UNKNOWN
```

Alias normalization occurs before the taxonomy lookup, but non-genre semantic sets must not become genres merely because of casing/punctuation.

- [ ] **Step 5: Implement the development-only updater and generate the complete snapshot**

`scripts/update_genre_taxonomy.py` must:

- request `https://musicbrainz.org/ws/2/genre/all?fmt=txt` with a meaningful Noqlen Meta User-Agent;
- use a finite timeout and bounded response size;
- reject non-UTF-8/empty responses;
- NFKC-normalize and trim names;
- reject duplicate casefold identities;
- write sorted canonical names with one trailing newline;
- print old/new counts and SHA-256 so the diff is reviewable;
- write only when invoked explicitly.

Run it once to create the committed `genres.txt`. Verify the resulting snapshot includes K-pop, Technical Death Metal, Progressive Metal, Melodic Death Metal, and Drum and Bass (using upstream canonical capitalization/spelling).

Do not ship a hand-written partial seed list. If the complete upstream snapshot cannot be obtained, stop this task rather than silently committing a reduced vocabulary.

- [ ] **Step 6: Add package-data declaration and prove installed-resource availability**

Add:

```toml
[tool.setuptools.package-data]
"beetsplug.noqlenmeta.genre_taxonomy" = ["genres.txt"]
```

Extend `tests/test_genre_taxonomy.py` so `DEFAULT_GENRE_TAXONOMY.snapshot_id` is stable/non-empty and the resource can be loaded through `importlib.resources`, not by repository-relative path.

- [ ] **Step 7: Run focused tests**

```bash
pytest tests/test_genre_taxonomy.py -q
ruff check beetsplug/noqlenmeta/genre_taxonomy scripts/update_genre_taxonomy.py tests/test_genre_taxonomy.py
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml beetsplug/noqlenmeta/genre_taxonomy scripts/update_genre_taxonomy.py tests/test_genre_taxonomy.py
git commit -m "feat: add packaged genre taxonomy"
```

---

### Task 2: Add immutable genre evidence and deterministic pure resolution

**Files:**
- Create: `beetsplug/noqlenmeta/genre_evidence.py`
- Create: `beetsplug/noqlenmeta/genre_resolution.py`
- Test: `tests/test_genre_resolution.py`

**Interfaces:**
- Consumes: `GenreTaxonomy` and `ProviderScope`.
- Produces: `GenreEvidenceKind.GENRE`, `.PROMOTED_STYLE`, `.COMMUNITY_TAG`.
- Produces: `GenreEvidence(genre, provider, scope, kind, confidence, source_id, source_url=None, weight=None)`.
- Produces: `GenreSettings(num_genres: int = 1, promote_styles: bool = True)` with range validation.
- Produces: `GenreResolution(genres: tuple[str, ...], evidence: tuple[GenreEvidence, ...], explanation: tuple[str, ...])`.
- Produces: `resolve_genres(evidence: Sequence[GenreEvidence], *, settings: GenreSettings, taxonomy: GenreTaxonomy = DEFAULT_GENRE_TAXONOMY, min_confidence: float = 0.0) -> GenreResolution`.

- [ ] **Step 1: Write failing evidence-validation tests**

Cover non-empty provider/source IDs, finite confidence in `0..1`, optional integer weight in `0..100`, valid `ProviderScope`, and `GenreSettings.num_genres` rejection for `0` and `11`.

Example:

```python

def test_genre_settings_default_to_one_genre_and_style_promotion() -> None:
    settings = GenreSettings()
    assert settings.num_genres == 1
    assert settings.promote_styles is True
```

- [ ] **Step 2: Write failing resolver behavior tests**

Use synthetic evidence only. Include these exact behavioral cases:

```python

def ev(name, provider, scope, kind=GenreEvidenceKind.GENRE, confidence=0.9, weight=None):
    return GenreEvidence(name, provider, scope, kind, confidence, "synthetic", weight=weight)


def test_reliable_track_scope_beats_release_and_artist() -> None:
    result = resolve_genres((
        ev("Drum and Bass", "musicbrainz", ProviderScope.TRACK),
        ev("K-pop", "musicbrainz", ProviderScope.ARTIST),
        ev("K-pop", "discogs", ProviderScope.RELEASE),
    ), settings=GenreSettings())
    assert result.genres == ("Drum and Bass",)


def test_weak_track_evidence_is_filtered_before_scope_preference() -> None:
    result = resolve_genres((
        ev("Experimental", "lastfm", ProviderScope.TRACK, GenreEvidenceKind.COMMUNITY_TAG, confidence=0.4, weight=11),
        ev("K-pop", "musicbrainz", ProviderScope.RELEASE, confidence=0.95),
        ev("K-pop", "discogs", ProviderScope.RELEASE, confidence=0.92),
    ), settings=GenreSettings(), min_confidence=0.8)
    assert result.genres == ("K-pop",)


def test_specific_promoted_style_beats_broad_discogs_genre() -> None:
    result = resolve_genres((
        ev("Rock", "discogs", ProviderScope.RELEASE, GenreEvidenceKind.GENRE),
        ev("Technical Death Metal", "discogs", ProviderScope.RELEASE, GenreEvidenceKind.PROMOTED_STYLE),
    ), settings=GenreSettings())
    assert result.genres == ("Technical Death Metal",)
```

Also cover:

- K-pop confirmed by three providers beating Pop confirmed by fewer providers at the same scope;
- three MusicBrainz rows count as one provider for consensus;
- Discogs genre + promoted style do not count as two providers;
- duplicate evidence collapse;
- `num_genres=3` returns three independently evidenced winners and does not append parents;
- canonical aliases dedupe to one genre;
- noise/non-genres never survive even if passed as evidence;
- identical inputs always produce identical order.

- [ ] **Step 3: Run tests and verify failure**

```bash
pytest tests/test_genre_resolution.py -q
```

Expected: FAIL because evidence/resolution types do not exist.

- [ ] **Step 4: Implement immutable evidence/settings types**

Keep validation local and explicit. Do not add a universal `score` property.

- [ ] **Step 5: Implement deterministic resolver without arithmetic provider scores**

Normalize every evidence label through `GenreTaxonomy.classify()` and retain only `GENRE` classifications at or above `min_confidence`.

Collapse duplicate evidence by `(canonical_genre.casefold(), provider.casefold(), scope, kind)`, retaining the strongest confidence/native weight for that exact key.

Build one profile per canonical genre. Sort profiles lexicographically using discrete signals in this order:

```text
1. best scope rank: TRACK=0, RELEASE=1, ARTIST=2
2. distinct provider count: larger first
3. evidence-kind rank: GENRE/PROMOTED_STYLE=0, COMMUNITY_TAG=1
4. broad rank: specific=0, broad=1
5. maximum eligible confidence: larger first
6. maximum provider-native weight (missing=-1): larger first
7. canonical casefold name ascending
```

`GENRE` and `PROMOTED_STYLE` intentionally share the same kind rank so a recognized specific Discogs style can beat a broad Discogs genre on specificity. `COMMUNITY_TAG` remains weaker at the same scope/provider-count conditions.

Return the first `settings.num_genres` profiles only. Never infer/add parents.

Populate `GenreResolution.evidence` with the normalized/deduped evidence supporting selected genres, stable-sorted by selected genre order then provider/scope/kind. Populate concise explanation entries such as `"Technical Death Metal: discogs promoted style"`; no numeric Noqlen score.

- [ ] **Step 6: Run resolver tests**

```bash
pytest tests/test_genre_resolution.py tests/test_genre_taxonomy.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add beetsplug/noqlenmeta/genre_evidence.py beetsplug/noqlenmeta/genre_resolution.py tests/test_genre_resolution.py
git commit -m "feat: add deterministic genre resolution"
```

---

### Task 3: Adapt existing release candidates and promote recognized styles

**Files:**
- Create: `beetsplug/noqlenmeta/genre_pipeline.py`
- Modify: `beetsplug/noqlenmeta/resolver.py`
- Test: `tests/test_genre_pipeline.py`
- Modify: `tests/test_resolver.py`

**Interfaces:**
- Consumes: already-collected `MetadataCandidate`, `ResolutionPolicy`, `GenreSettings`, taxonomy.
- Produces: `genre_evidence_from_release_candidates(candidates, *, policy, settings, taxonomy=DEFAULT_GENRE_TAXONOMY) -> tuple[GenreEvidence, ...]`.
- Produces: `resolve_release_genre_decision(current_value, candidates, *, policy, settings, taxonomy=DEFAULT_GENRE_TAXONOMY) -> FieldDecision | None`.
- Produces aggregate selected candidate provenance `provider="noqlen"` only inside the specialized `FieldDecision`; it is not registered as a provider and never participates in provider enablement/authority lookup.

- [ ] **Step 1: Write failing candidate-to-evidence tests**

Use `MetadataCandidate` fixtures to prove:

- Discogs `genres=("Rock",)` -> release `GENRE` evidence.
- Discogs `styles=("Technical Death Metal",)` -> release `PROMOTED_STYLE` evidence when `promote_styles=True`.
- the same style produces no genre evidence when `promote_styles=False`.
- an unrecognized Discogs style is not promoted.
- Last.fm genre candidate becomes `COMMUNITY_TAG` evidence.
- iTunes genre candidate becomes `GENRE` evidence.
- providers disabled for the `genres` rule or below `min_confidence` do not contribute.
- style promotion is allowed even when persistence of `fields.styles` is disabled, because `promote_styles` independently controls use as classification evidence.

- [ ] **Step 2: Write failing aggregate `FieldDecision` tests**

Cover missing current value -> `PROPOSE`; same existing tuple -> `KEEP`; conflicting existing tuple with `preserve_existing=True` -> `REVIEW`; `preserve_existing=False` -> `PROPOSE`; disabled `fields.genres` -> no genre decision/change.

The selected aggregate candidate must have:

```python
selected.field == "genres"
selected.provider == "noqlen"
selected.value == ("Technical Death Metal",)
```

Its `source_id` should be `f"genre-taxonomy:{taxonomy.snapshot_id}"`; its confidence is the maximum confidence among evidence supporting the selected genres, not an invented aggregate score. The `FieldDecision.reason` must include the selected genre plus provider/kind provenance in stable order.

- [ ] **Step 3: Run focused tests and verify failure**

```bash
pytest tests/test_genre_pipeline.py -q
```

Expected: FAIL because the pipeline does not exist.

- [ ] **Step 4: Implement candidate adaptation and specialized genre decision**

For each candidate:

- ignore fields other than `genres` and `styles`;
- require the candidate provider to be enabled in policy and authorized for `genres`;
- require candidate confidence >= the genre field rule threshold;
- expand tuple/list genre/style values into one evidence row per label;
- classify labels through the packaged taxonomy;
- set all current adapter evidence to `ProviderScope.RELEASE`;
- map provider `lastfm` genre labels to `COMMUNITY_TAG`, all other genre labels to `GENRE`;
- map recognized Discogs styles to `PROMOTED_STYLE` only when `promote_styles=True`.

Do not mutate the original candidate sequence.

- [ ] **Step 5: Update future genre authority without pretending MusicBrainz emits genres today**

Change only the default authority order in `resolver.py`:

```python
"genres": ("musicbrainz", "discogs", "lastfm", "itunes"),
```

Do not add `genres` to `MUSICBRAINZ_SPEC.supported_fields` in this plan; that capability becomes truthful only when Semantic Enrichment implements `inc=genres`.

Generic `resolve_metadata()` must remain free of genre-specific classification branches.

- [ ] **Step 6: Run pipeline/resolver tests**

```bash
pytest tests/test_genre_pipeline.py tests/test_genre_resolution.py tests/test_resolver.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add beetsplug/noqlenmeta/genre_pipeline.py beetsplug/noqlenmeta/resolver.py tests/test_genre_pipeline.py tests/test_resolver.py
git commit -m "feat: adapt genre evidence from release metadata"
```

---

### Task 4: Route release planning through the genre pipeline without changing persistence authority

**Files:**
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Test: `tests/test_v2_foundation_command.py`
- Test: `tests/release/test_v1_workflows.py`

**Interfaces:**
- Consumes: `resolve_release_genre_decision()` and `GenreSettings`.
- Changes only: `NoqlenMetaPlugin._build_change_plan_for_release()` decision construction.
- Preserves: `map_change_plan_to_beets`, `map_change_plan_to_library_album`, database application, file-sync planning, preview/apply/write semantics.

- [ ] **Step 1: Write failing importer/library parity tests at the planning boundary**

Patch existing provider candidate collection only; do not contact networks. For both selected-import release and existing-library Album flows, supply:

```text
Discogs genres: Rock
Discogs styles: Technical Death Metal
```

with `fields.genres=true`, `genres.num_genres=1`, `genres.promote_styles=true`, and an eligible Discogs policy. Assert the prepared target proposes `genres=("Technical Death Metal",)` while `styles` remains `("Technical Death Metal",)` through the existing style mapping.

Add a `num_genres=2` case with independently supported second genre and assert both values reach the existing multivalue `genres` target in stable order.

- [ ] **Step 2: Run focused command/workflow tests and verify failure**

```bash
pytest tests/test_v2_foundation_command.py tests/release/test_v1_workflows.py -q
```

Expected: new genre-pipeline assertions FAIL because `_build_change_plan_for_release()` still sends raw genre tuples directly to `resolve_metadata()`.

- [ ] **Step 3: Add one plugin helper for validated genre settings**

Read only:

```python
GenreSettings(
    num_genres=self.config["genres"]["num_genres"].get(int),
    promote_styles=self.config["genres"]["promote_styles"].get(bool),
)
```

Let `GenreSettings` enforce `1..10`. Convert invalid user config to the same user-facing settings error style already used by resolution configuration; do not silently clamp.

- [ ] **Step 4: Integrate specialized genre decision in `_build_change_plan_for_release()`**

Keep provider collection unchanged. After `candidates` are collected:

```python
ordinary_candidates = tuple(c for c in candidates if c.field != "genres")
ordinary_decisions = resolve_metadata(current_values, ordinary_candidates, policy)
genre_decision = resolve_release_genre_decision(
    current_values.get("genres"),
    candidates,
    policy=policy,
    settings=self._genre_settings(),
)
decisions = ordinary_decisions + ((genre_decision,) if genre_decision is not None else ())
return build_change_plan(tuple(sorted(decisions, key=lambda decision: decision.field)))
```

Do not remove `styles` from `ordinary_candidates`: styles must still be independently resolved/persisted. Do not modify `build_change_plan()`, application layers, or file-sync writer.

- [ ] **Step 5: Prove existing genre DB/file behavior remains intact**

Run existing genre mapping/file-sync tests plus new parity tests. Ensure `--apply --write` still uses the existing `genres -> genres` file mapping and no classifier work is triggered by `--write` itself.

```bash
pytest tests/test_beets_mapping.py tests/test_library_mapping.py tests/test_file_sync.py tests/test_v2_foundation_command.py tests/release/test_v1_workflows.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add beetsplug/noqlenmeta/__init__.py tests/test_v2_foundation_command.py tests/release/test_v1_workflows.py
git commit -m "feat: integrate genre resolution into release planning"
```

---

### Task 5: Remove the runtime LastGenre vocabulary dependency

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/lastfm.py`
- Modify: `tests/test_lastfm_provider.py`

**Interfaces:**
- Removes: `load_beets_genre_vocabulary()` and all `importlib.util.find_spec("beetsplug.lastgenre")` / LastGenre resource reads.
- `LastFmProvider` may accept injected `GenreTaxonomy` for tests; default is `DEFAULT_GENRE_TAXONOMY`.
- Preserves current Foundation network behavior: album `getTopTags`, identity match validation, `_MIN_TAG_WEIGHT=10`, `_MAX_GENRES=3`, pacing/bounds/cache, and one release `MetadataCandidate(field="genres", ...)`.
- Semantic Enrichment later replaces album-only collection with track/release/artist evidence production.

- [ ] **Step 1: Replace LastGenre-dependent tests with Noqlen-taxonomy tests**

Add a test that monkeypatches `importlib.util.find_spec` (or removes `beetsplug.lastgenre` from availability) and proves `LastFmProvider` still accepts representative valid tags through the packaged taxonomy. There must be no test that requires LastGenre to be discoverable.

Add payload cases containing:

```text
K-pop count=80
Technical Death Metal count=60
seen live count=50
2024 count=40
Energetic count=30
```

Assert only recognized genre labels are emitted as genres; semantic/noise labels are rejected.

- [ ] **Step 2: Run Last.fm tests and verify failure against current implementation**

```bash
pytest tests/test_lastfm_provider.py -q
```

Expected: the new no-LastGenre test FAILS because current code discovers/reads `beetsplug.lastgenre/genres.txt`.

- [ ] **Step 3: Replace vocabulary discovery with injected/default `GenreTaxonomy`**

During `_normalize_payload`, retain existing identity/count validation, then classify each tag through taxonomy. Accept only `GenreSemanticCategory.GENRE`; preserve stable API tag order and existing max-three behavior. Store canonical taxonomy spelling in the emitted tuple.

Do not add Last.fm track/artist calls, fallback changes, or new public thresholds in this task.

- [ ] **Step 4: Run Last.fm and pipeline tests**

```bash
pytest tests/test_lastfm_provider.py tests/test_genre_pipeline.py tests/test_genre_taxonomy.py -q
```

Expected: PASS with no LastGenre runtime requirement.

- [ ] **Step 5: Search for residual architectural dependency**

```bash
grep -R "beetsplug\.lastgenre\|genres\.txt" -n beetsplug tests | cat
```

Expected: no `beetsplug.lastgenre` reference; `genres.txt` references point only to Noqlen's packaged taxonomy/tests.

- [ ] **Step 6: Commit**

```bash
git add beetsplug/noqlenmeta/providers/lastfm.py tests/test_lastfm_provider.py
git commit -m "refactor: decouple genres from LastGenre"
```

---

### Task 6: Add genre configuration, public docs, package verification, and final regression gate

**Files:**
- Modify: `beetsplug/noqlenmeta/configuration.py`
- Modify: `site-docs/reference/configuration.md`
- Modify: `site-docs/reference/fields.md`
- Modify: `site-docs/examples/full-config.yaml`
- Modify: `tests/docs/test_public_documentation.py`
- Modify: `tests/test_v2_foundation_command.py`
- Modify: `pyproject.toml` only if Task 1 package-data verification exposes a packaging issue.

**Interfaces:**
- Public config:

```yaml
genres:
  num_genres: 1
  promote_styles: true
```

- `fields.genres` remains separate and defaults to `true`.
- Documentation must state: one specific resolved genre by default; `num_genres` changes only output count; no implicit parents; recognized styles may be promoted while remaining in `styles`; Noqlen Meta does not require LastGenre.

- [ ] **Step 1: Write failing config/default tests**

Assert:

```python
config = default_config()
assert config["fields"]["genres"] is True
assert config["genres"] == {"num_genres": 1, "promote_styles": True}
```

At command/config boundary, assert `num_genres=0` and `11` are rejected before provider work; `num_genres=3` is accepted; non-boolean `promote_styles` follows Confuse/type validation rather than truthiness coercion.

- [ ] **Step 2: Run focused config tests and verify failure**

```bash
pytest tests/test_v2_foundation_command.py tests/docs/test_public_documentation.py -q
```

Expected: new config assertions FAIL until defaults/docs are wired.

- [ ] **Step 3: Add config defaults and concise docs**

Add the `genres` subtree beside `fields`/`providers`, not inside `fields`.

Document the model without exposing internal ranking knobs. Explicitly distinguish:

```text
genres = Noqlen-resolved navigation/classification output
styles = source style/subgenre metadata preserved independently
```

State that default one-genre output favors the most specific trustworthy result; `num_genres > 1` selects additional independently evidenced winners, not parent expansion.

- [ ] **Step 4: Run focused tests and docs checks**

```bash
pytest tests/test_genre_taxonomy.py tests/test_genre_resolution.py tests/test_genre_pipeline.py tests/test_lastfm_provider.py tests/test_v2_foundation_command.py tests/docs/test_public_documentation.py -q
python scripts/check_public_docs.py
mkdocs build --strict
```

Expected: PASS.

- [ ] **Step 5: Verify the built artifacts actually contain the taxonomy**

```bash
rm -rf dist build
python -m build
python -m twine check dist/*
python - <<'PY'
import glob, zipfile
wheel = glob.glob('dist/*.whl')[0]
with zipfile.ZipFile(wheel) as zf:
    names = zf.namelist()
assert any(name.endswith('beetsplug/noqlenmeta/genre_taxonomy/genres.txt') for name in names)
print('taxonomy package data: OK')
PY
```

Expected: wheel and sdist pass metadata validation and the wheel contains the packaged taxonomy.

- [ ] **Step 6: Run the complete local verification gate**

```bash
ruff check .
pytest -q
python scripts/check_public_docs.py
mkdocs build --strict
python -m build
python -m twine check dist/*
python scripts/check_repo_contamination.py
git diff --check origin/docs/v2-enrichment-design...HEAD
```

If dedicated beets boundary environments are available, also run the repository's focused compatibility suite against beets `2.12.0` and latest `<3`. Report exact versions/results; do not substitute an unverified claim.

- [ ] **Step 7: Review scope and regression invariants before push**

Confirm from the final diff:

- no new MusicBrainz `inc=genres` request;
- no new Last.fm track/artist request;
- no LastGenre runtime reference;
- no provider registry entry named `noqlen`/`noqlen-genre`;
- no parent-genre expansion tree;
- no public provider weight tuning;
- `styles` persistence is unchanged except being usable as classification evidence;
- Identity/AcoustID/file-sync authority semantics are unchanged;
- taxonomy file is complete package data, not a partial hand-maintained seed.

- [ ] **Step 8: Commit final docs/config adjustments**

```bash
git add beetsplug/noqlenmeta/configuration.py site-docs tests/docs tests/test_v2_foundation_command.py pyproject.toml
git commit -m "docs: expose genre foundation defaults"
```

- [ ] **Step 9: Push the existing branch and use PR #22 CI as the final fresh gate**

```bash
git push origin feat/v2-foundation
```

Do not open another PR. Do not merge.

After push, report:

- exact HEAD SHA;
- commits added by this plan;
- exact local verification results;
- working tree status.

The PR-triggered GitHub Actions matrix must then be inspected fresh on that HEAD before anyone claims the Foundation is green again.

---

## Plan Self-Review Checklist

Before execution, verify this plan against `docs/superpowers/specs/2026-08-10-genre-foundation-design.md`:

- Taxonomy independence: Task 1 + Task 5.
- Complete packaged MusicBrainz-derived snapshot: Task 1.
- Aliases/noise/non-genre separation: Task 1.
- Broad-vs-specific without hierarchy: Task 1 + Task 2.
- `GenreEvidence` provenance/scope/kind/confidence/weight: Task 2.
- Deterministic no-magic-score ranking: Task 2.
- Track > Release > Artist only after reliability: Task 2.
- Distinct-provider consensus: Task 2.
- Discogs recognized-style promotion and preservation of `styles`: Task 3 + Task 4.
- One genre by default and configurable `1..10`: Task 2 + Task 6.
- No automatic parents: Task 2 + Task 6.
- Generic resolver remains genre-agnostic: Task 3 + Task 4.
- Existing provider data proves the architecture now; new online collection remains deferred: Task 3-5.
- Existing DB/file-write authority preserved: Task 4 + Task 6.
- Explainable provenance without numeric Noqlen scores: Task 2 + Task 3.
- Packaging and cross-version CI gate: Task 6.

No implementation task in this plan requires a new runtime dependency or a new provider network capability.