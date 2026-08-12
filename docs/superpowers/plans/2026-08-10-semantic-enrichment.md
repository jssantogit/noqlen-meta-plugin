# Noqlen Meta v2 Semantic Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Semantic Enrichment phase so exact MusicBrainz identities produce useful zero-credential semantic metadata, while Discogs and Last.fm improve coverage without weakening deterministic resolution, import/library parity, or write safety.

**Architecture:** Extend the Foundation's `RELEASE`, `TRACK`, and `ARTIST` scopes. Providers emit structured metadata and normalized semantic evidence; pure resolvers choose canonical values; only the existing change-plan/application layer may mutate beets or media files. One command-lifetime exact-entity cache and field-aware Last.fm fallback prevent redundant provider work.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, mediafile/mutagen through beets, requests, pytest, ruff, MkDocs, existing Noqlen provider/change-plan/file-sync infrastructure.

## Global Constraints

- Branch: `feat/semantic-enrichment`.
- Approved spec: `docs/superpowers/specs/2026-08-10-semantic-enrichment-design.md` at commit `a857b1cd5b88d39e2e1e7393b455645e1867c532`.
- Foundation base: `f651dafc3691d33287b2dca38f960a4c5b533f42`.
- MusicBrainz uses exact MBIDs already selected/stored by beets/Noqlen; no fuzzy identity search.
- Discogs stays opt-in and remains the structured style authority.
- Last.fm stays opt-in and uses field-aware Track -> Release -> Artist fallback.
- `moods.max_moods` defaults to `1`; valid range is integer `1..10`.
- Each accepted community term has one category only: `GENRE`, `STYLE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, or `NOISE`.
- Unknown community tags are never persisted automatically.
- `lyrics_languages` and `artist_languages` store canonical three-letter language codes.
- `artist_languages` derives only from identified Works in the current target; never crawl an artist's full catalogue.
- `artist_countries` is geographic identification/origin, not citizenship. Never infer it from artist name, language, release country, title script, or area-name text matching.
- Provider/network failures are local when safe; structural plan/file-safety failures remain blocking.
- No persistent API cache and no request-budget setting.
- `--write` never triggers extra provider calls or analysis.
- Importer and existing-library paths share semantic contexts, evidence, classification, resolution, and canonical values.
- Preserve identity/AcoustID behavior, Genre Foundation ranking, `genres.num_genres`, `genres.promote_styles`, and legacy scalar `style` fallback.
- Do not implement Cover Art Archive, artwork download/embed, BPM, `[audio]`, local ML mood analysis, or a version bump.
- Do not add another mandatory beets plugin dependency.
- CI compatibility remains beets `2.12.0` and latest beets `<3`.

---

## Task 1: Semantic classifier, mood/style resolver, and config

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_tags.py`
- Create: `beetsplug/noqlenmeta/semantic_resolution.py`
- Modify: `beetsplug/noqlenmeta/domain.py`
- Modify: `beetsplug/noqlenmeta/configuration.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Create: `tests/test_semantic_tags.py`
- Create: `tests/test_semantic_resolution.py`
- Modify: `tests/test_v2_foundation_command.py`

**Interfaces produced:**
- `SemanticCategory` enum with `GENRE`, `STYLE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, `NOISE`.
- `SemanticTagEvidence` immutable value carrying canonical term, category, provider, `ProviderScope`, confidence, source ID/URL, native weight, and raw tag.
- `SemanticEvidenceBundle` containing `metadata`, `genres`, and classified semantic `tags` tuples.
- `classify_semantic_tag(raw_tag, provider, scope, confidence, source_id, source_url, weight) -> SemanticTagEvidence | None`.
- `resolve_styles(structured, community) -> tuple[str, ...]`.
- `resolve_moods(evidence, max_moods) -> tuple[str, ...]`.

- [ ] **Step 1: Write RED classifier tests**

Use these exact canonical cases:

```python
CASES = (
    ("melancholy", SemanticCategory.MOOD, "Melancholic"),
    ("melancholic", SemanticCategory.MOOD, "Melancholic"),
    ("dreamy", SemanticCategory.MOOD, "Dreamy"),
    ("atmospheric", SemanticCategory.MOOD, "Atmospheric"),
    ("progressive metal", SemanticCategory.STYLE, "Progressive Metal"),
    ("k-pop", SemanticCategory.GENRE, "K-pop"),
    ("korean", SemanticCategory.ORIGIN, "Korean"),
    ("seen live", SemanticCategory.NOISE, "Seen Live"),
)
```

Also assert blank/unknown tags return `None`, genre recognition reuses the existing Noqlen genre taxonomy, and one raw tag produces only one category.

Run:

```bash
pytest -q tests/test_semantic_tags.py
```

Expected: FAIL because `semantic_tags.py` does not exist.

- [ ] **Step 2: Implement deterministic classification**

Use this normalization helper exactly:

```python
import unicodedata


def semantic_identity(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
```

Classification order:

```text
NOISE allowlist
-> existing Genre Foundation classifier
-> STYLE allowlist
-> MOOD aliases/canonical allowlist
-> ORIGIN allowlist
-> DESCRIPTOR allowlist
-> unknown => no evidence
```

Keep non-genre vocabularies deliberately compact and reviewed; do not bulk-import Forge/LastGenre tag lists.

- [ ] **Step 3: Write RED resolver tests**

Required outcomes:

```text
Track Melancholic weight 8 + Track Dreamy weight 7; max_moods=1 -> Melancholic
Release Dreamy from MusicBrainz + Release Dreamy from Last.fm + Release Melancholic only from MusicBrainz -> Dreamy
Discogs structured styles Progressive Metal + Technical Death Metal plus Last.fm Alternative Metal -> preserve the Discogs tuple
max_moods=3 with only two eligible moods -> return two; never pad
```

Run:

```bash
pytest -q tests/test_semantic_resolution.py
```

Expected: FAIL because `semantic_resolution.py` does not exist.

- [ ] **Step 4: Implement pure resolvers**

Use ordered policy components, not one summed magic score:

```text
filter semantic/quality eligibility first
-> scope relevance
-> distinct-provider corroboration
-> evidence strength
-> native provider weight
-> stable canonical/input order
```

Structured Discogs styles are preserved as the primary ordered style tuple. Community `STYLE` evidence is fallback coverage only when structured style evidence is absent.

- [ ] **Step 5: Add `moods.max_moods`**

Add this default:

```yaml
moods:
  max_moods: 1
```

Command tests must accept integer `1` and `3`, reject `0`, `11`, `True`, and string `"1"`, and prove invalid config is rejected before provider work.

- [ ] **Step 6: Verify and commit**

```bash
pytest -q tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
ruff check beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/configuration.py tests/test_semantic_tags.py tests/test_semantic_resolution.py
git add beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/configuration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
git commit -m "feat: add semantic tag classification"
```

---

## Task 2: Command-lifetime cache and multi-scope provider specs

**Files:**
- Create: `beetsplug/noqlenmeta/provider_cache.py`
- Modify: `beetsplug/noqlenmeta/providers/specs.py`
- Create: `tests/test_provider_cache.py`
- Modify: `tests/test_provider_specs.py`

**Interfaces produced:**
- `EntityCacheKey(provider: str, entity_type: str, entity_id: str)` immutable key.
- `CommandEntityCache.get_or_fetch(key, fetcher) -> Mapping[str, object] | None`.

- [ ] **Step 1: Write RED cache tests**

Test exactly:

```text
successful payload fetched twice by same key -> fetcher called once
definitive None fetched twice by same key -> fetcher called once
first call raises RequestException -> failure is not cached; second call executes fetcher and can succeed
```

Run:

```bash
pytest -q tests/test_provider_cache.py
```

- [ ] **Step 2: Implement the cache**

Core behavior:

```python
class CommandEntityCache:
    def __init__(self) -> None:
        self._payloads: dict[EntityCacheKey, Mapping[str, object]] = {}
        self._missing: set[EntityCacheKey] = set()

    def get_or_fetch(self, key: EntityCacheKey, fetcher):
        if key in self._payloads:
            return self._payloads[key]
        if key in self._missing:
            return None
        payload = fetcher()
        if payload is None:
            self._missing.add(key)
            return None
        self._payloads[key] = payload
        return payload
```

Validate all key strings as non-empty normalized values in `EntityCacheKey.__post_init__`.

- [ ] **Step 3: Add multi-scope specs**

The registry must contain all six keys simultaneously:

```text
musicbrainz / RELEASE
musicbrainz / TRACK
musicbrainz / ARTIST
lastfm / RELEASE
lastfm / TRACK
lastfm / ARTIST
```

Advertised semantic capability after this phase:

```text
MusicBrainz TRACK -> genres, moods, lyrics_languages
MusicBrainz ARTIST -> genres, moods, artist_countries, artist_areas
Last.fm TRACK -> genres, styles, moods
Last.fm RELEASE -> genres, styles, moods
Last.fm ARTIST -> genres, styles, moods
```

`artist_languages` is derived from current-target Works and is not an Artist-provider capability.

- [ ] **Step 4: Verify registry behavior and commit**

```bash
pytest -q tests/test_provider_cache.py tests/test_provider_specs.py
ruff check beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py tests/test_provider_specs.py
git add beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py tests/test_provider_specs.py
git commit -m "refactor: add semantic provider cache scopes"
```

---

## Task 3: MusicBrainz exact semantic evidence

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/musicbrainz.py`
- Create: `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py`
- Modify: `beetsplug/noqlenmeta/genre_pipeline.py`
- Modify: `tests/test_musicbrainz_provider.py`
- Create: `tests/test_musicbrainz_semantic.py`
- Modify: `tests/test_genre_pipeline.py`
- Modify: `tests/test_genre_resolution.py`

**Interfaces produced:**
- `MusicBrainzSemanticClient` exact cached lookup methods for Release, Recording, Work, Artist, Area.
- `MusicBrainzTrackProvider.get_semantic_evidence(context) -> SemanticEvidenceBundle`.
- `MusicBrainzArtistProvider.get_semantic_evidence(context) -> SemanticEvidenceBundle`.
- Release provider keeps existing `get_candidates()` and gains semantic evidence collection without breaking ordinary release metadata.

- [ ] **Step 1: Write RED release union-lookup test**

Inject a release fetch boundary that records requested includes. One release lookup must satisfy existing release metadata plus enabled semantic needs. Preserve exact response-MBID validation and existing provider error semantics.

- [ ] **Step 2: Write RED Recording -> Work language tests**

Cover:

```text
one Recording -> two Works -> kor, eng, kor => lyrics_languages=(kor, eng)
two tracks -> same Work MBID => Work fetch count 1
Work with no usable language => no language candidate
instrumental/no-lyrics Work => no fabricated language
malformed language token => ignored; never translated or guessed
```

- [ ] **Step 3: Write RED genre/tag scope tests**

Use this representative Recording payload shape:

```python
RECORDING_PAYLOAD = {
    "id": RECORDING_MBID,
    "genres": [{"name": "k-pop", "count": 9}],
    "tags": [
        {"name": "dreamy", "count": 8},
        {"name": "seen live", "count": 2},
    ],
    "relations": [],
}
```

Expected: direct Track-scope `K-pop` genre evidence, Track-scope `Dreamy` mood evidence, and no persisted value from `seen live`. Add Release- and Artist-scope equivalents.

- [ ] **Step 4: Write RED artist geography tests**

Cover:

```text
main area Salvador + structural Area ancestry/ISO reaches Brazil -> Salvador + Brazil
trustworthy main city but country unresolved -> area only
main area absent + structurally trustworthy begin-area -> controlled fallback allowed
main area present + conflicting begin-area -> main area wins
```

Never derive country by parsing an area-name string.

- [ ] **Step 5: Implement exact cached lookups and normalization**

Cache namespaces:

```text
musicbrainz/release/<MBID>
musicbrainz/recording/<MBID>
musicbrainz/work/<MBID>
musicbrainz/artist/<MBID>
musicbrainz/area/<MBID>
```

Rules:

```text
response ID mismatch -> ProviderError, not negative cache
direct MB genres -> direct GenreEvidence at entity scope
MB community GENRE tag -> weaker community GenreEvidence
MB STYLE/MOOD tag -> SemanticTagEvidence
MB ORIGIN tag -> classification only; never artist geography
Work languages -> normalized three-letter codes, ordered/deduplicated
artist geography -> Area structure/type/ISO/ancestry only
```

- [ ] **Step 6: Integrate genre scopes without changing ranking**

Track/Release/Artist evidence joins the current specialized genre resolver. Quality filtering still occurs before scope preference; corroboration counts distinct providers, not rows.

- [ ] **Step 7: Verify and commit**

```bash
pytest -q tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py beetsplug/noqlenmeta/genre_pipeline.py tests/test_musicbrainz_semantic.py
git add beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py beetsplug/noqlenmeta/genre_pipeline.py tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add MusicBrainz semantic evidence"
```

---

## Task 4: Last.fm lazy fallback and Discogs style authority

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/lastfm.py`
- Modify: `beetsplug/noqlenmeta/semantic_resolution.py`
- Modify: `tests/test_lastfm_provider.py`
- Modify: `tests/test_discogs_provider.py`
- Modify: `tests/test_semantic_resolution.py`
- Modify: `tests/test_genre_pipeline.py`

- [ ] **Step 1: Write RED Last.fm multi-scope tests**

Track, Release, and Artist tag results must retain provider, scope, source identity, native weight, and canonical category. Noise/unknown terms never become metadata.

- [ ] **Step 2: Write RED field-aware fallback tests**

Use explicit call counters:

```text
Track resolves genre+mood -> Release 0, Artist 0
Track resolves genre only -> Release can run for mood
Release resolves remaining mood -> Artist 0
Track+Release insufficient -> Artist can run for unresolved fields
```

A resolved genre must not suppress a later call needed only for mood/style.

- [ ] **Step 3: Implement scoped Last.fm normalization**

Reuse the existing authenticated request boundary/error behavior. Prefer a known MBID when the called endpoint accepts it; otherwise use exact already-identified artist/title/album context. Do not add search/disambiguation. Route every returned community tag through `classify_semantic_tag()`.

- [ ] **Step 4: Preserve Discogs structured styles**

No provider change is required unless an existing regression test exposes a normalization loss. The resolver consumes the current structured Discogs `styles` tuple directly. Existing style->genre promotion remains independent and only occurs under `genres.promote_styles` plus genre-taxonomy recognition.

- [ ] **Step 5: Verify and commit**

```bash
pytest -q tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/semantic_resolution.py tests/test_lastfm_provider.py tests/test_semantic_resolution.py
git add beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/semantic_resolution.py tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add scoped semantic fallback"
```

---

## Task 5: Shared orchestration, derived artist languages, parity, and outcomes

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_enrichment.py`
- Modify: `beetsplug/noqlenmeta/integration.py`
- Modify: `beetsplug/noqlenmeta/track_integration.py`
- Modify: `beetsplug/noqlenmeta/library_integration.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Create: `tests/test_semantic_enrichment.py`
- Modify: `tests/test_v2_foundation_command.py`
- Modify: `tests/test_beets_integration.py`

**Interfaces produced:**
- `SemanticFieldStatus`: `RESOLVED`, `NO_EVIDENCE`, `UNAVAILABLE`, `CONFLICT`, `BLOCKED`.
- `SemanticFieldOutcome`: field, status, optional canonical value, provenance tuple, reason.
- `SemanticEnrichmentResult`: resolved metadata candidates plus field outcomes.
- `derive_artist_languages(track_languages) -> tuple[str, ...]` pure helper.
- `collect_semantic_enrichment(...) -> SemanticEnrichmentResult` single semantic orchestration entry point for importer/library targets.

- [ ] **Step 1: Write RED field-gating tests**

With only `genres` enabled, Work fetch count must be zero and no mood/language outcomes exist. With lyrics language enabled and moods disabled, only language-required capabilities are collected. `--write` is not an input to semantic collection and cannot change provider call counts.

- [ ] **Step 2: Write RED contextual artist-language tests**

Use:

```python
TRACK_LANGUAGES = (
    (1, ("kor",)),
    (1, ("kor", "eng")),
    (2, ("jpn",)),
)
EXPECTED_ARTIST_LANGUAGES = ("kor", "eng", "jpn")
```

Assert the helper returns `EXPECTED_ARTIST_LANGUAGES` and performs no network work. Add credit-order/dedup tests for countries/areas.

- [ ] **Step 3: Write RED outcome-state tests**

Exact distinctions:

```text
Work exists but no language -> NO_EVIDENCE
Work lookup network failure -> UNAVAILABLE
eligible semantic evidence with no deterministic winner -> CONFLICT
lossless application mapping unavailable -> BLOCKED
safe selected value -> RESOLVED
```

A local field/provider failure must not erase unrelated successful candidates.

- [ ] **Step 4: Implement the shared collection sequence**

```text
compute enabled semantic fields
-> build exact release/track/artist contexts from existing IDs
-> create/reuse one CommandEntityCache for command execution
-> collect required MusicBrainz entity evidence
-> combine configured Discogs structured evidence
-> resolve currently resolvable fields
-> if Last.fm enabled, Track -> Release -> Artist only for still-unresolved community fields
-> resolve genres/styles/moods
-> derive artist_languages from current-target Work languages
-> aggregate artist areas/countries in credit order
-> return candidates + explicit outcomes
```

`collect_semantic_enrichment()` never writes DB/files.

- [ ] **Step 5: Wire existing-library path**

Use `context_from_library_album()` and `context_from_library_item()` plus Artist-context extraction in `library_integration.py`. Preserve Foundation command-wide preflight before any DB mutation under `--apply --write`.

- [ ] **Step 6: Wire importer path without re-identification**

`_import_task_choice` already receives beets-selected `AlbumInfo`/`TrackInfo`. Extend `integration.py` and `track_integration.py` so these exact IDs feed the same semantic orchestration used by existing-library targets. Do not add another importer-specific classifier/resolver.

- [ ] **Step 7: Add parity and preview tests**

For the same deterministic identified target, importer and library paths must resolve identical canonical values for:

```text
genres
styles
moods
lyrics_languages
artist_languages
artist_countries
artist_areas
```

Normal output shows resolved value + useful provenance and explicit `no-evidence`, `unavailable`, `conflict`, or `blocked` when relevant. Rejected raw tags such as `seen live` do not appear in normal output.

- [ ] **Step 8: Verify and commit**

```bash
pytest -q tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
ruff check beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/integration.py beetsplug/noqlenmeta/track_integration.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_enrichment.py
git add beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/integration.py beetsplug/noqlenmeta/track_integration.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
git commit -m "feat: integrate semantic enrichment pipeline"
```

---

## Task 6: Lossless semantic file sync, docs, and final verification

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_media.py`
- Modify: `beetsplug/noqlenmeta/file_sync.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Create: `tests/test_semantic_media.py`
- Modify: `tests/test_file_sync.py`
- Modify: `tests/test_v2_foundation_command.py`
- Modify: `README.md`
- Modify: `site-docs/reference/configuration.md`
- Modify: `site-docs/concepts/preview-apply-write.md`

Use beets `BeetsPlugin.add_media_field()` / `MediaField` extension points. Do not bypass MediaFile with direct ad-hoc Mutagen writes.

- [ ] **Step 1: Write RED real-file semantic round-trip tests**

For every semantic field enabled for file sync, write an ordered multivalue value to a copied real media fixture, reopen it through `MediaFile`, and assert exact value/order. Fields under test:

```text
styles
moods
lyrics_languages
artist_languages
artist_countries
artist_areas
```

Include values with spaces/hyphens. A descriptor/format combination that cannot round-trip losslessly must not be enabled in the production mapping table.

Run:

```bash
pytest -q tests/test_semantic_media.py tests/test_file_sync.py
```

- [ ] **Step 2: Register semantic MediaFile descriptors**

Create descriptors in `semantic_media.py`; register them from `NoqlenMetaPlugin.__init__()` using `add_media_field()`. Keep canonical DB field names unchanged. Enable a field in `file_sync` only after the Step 1 real-file test proves lossless round-trip. Do not serialize tuples with an ambiguous display separator merely to avoid a blocker.

- [ ] **Step 3: Extend Foundation file sync safely**

Preserve global preflight, candidate save/verify, stale checks, recovery artifacts, and final reopen/read verification. Unsupported lossless mappings remain explicit blockers before DB mutation under `--apply --write`.

- [ ] **Step 4: Add command-level observable write test**

With deterministic semantic candidates and a temporary real media file, invoke `--apply --write --all`, reopen the library DB and the actual media file, and assert both contain the same semantic values. Do not rely only on `FileSyncResult` flags.

- [ ] **Step 5: Update docs**

Document exact defaults:

```yaml
moods:
  max_moods: 1

providers:
  musicbrainz:
    enabled: true
  discogs:
    enabled: false
  lastfm:
    enabled: false
```

Also document exact-ID MusicBrainz semantics, Discogs structured styles, Last.fm lazy fallback, three-letter language fields, contextual `artist_languages`, artist geographic-identification semantics, semantic media mappings actually implemented, `--write` not triggering collection, and Artwork/BPM remaining for the next phase.

- [ ] **Step 6: Run focused semantic/file suites**

```bash
pytest -q \
  tests/test_semantic_tags.py \
  tests/test_semantic_resolution.py \
  tests/test_provider_cache.py \
  tests/test_musicbrainz_provider.py \
  tests/test_musicbrainz_semantic.py \
  tests/test_lastfm_provider.py \
  tests/test_discogs_provider.py \
  tests/test_genre_pipeline.py \
  tests/test_genre_resolution.py \
  tests/test_semantic_enrichment.py \
  tests/test_semantic_media.py \
  tests/test_file_sync.py \
  tests/test_v2_foundation_command.py \
  tests/test_beets_integration.py
```

- [ ] **Step 7: Run exact CI-equivalent repository checks**

```bash
ruff check .
pytest -m "not live"
python scripts/check_repo_contamination.py
python scripts/check_public_docs.py
mkdocs build --strict
python -m build
python -m twine check --strict dist/*
python scripts/check_distribution.py dist
```

- [ ] **Step 8: Run exact beets compatibility test set in two clean environments**

For beets `2.12.0`, install the project with that constraint and run:

```bash
pytest \
  tests/test_plugin_loads.py \
  tests/test_beets_integration.py \
  tests/test_library_cli.py \
  tests/identity/test_library_identity_command.py \
  tests/identity/test_identity_tag_command.py
```

Repeat the same test command in a clean environment with `beets<3` resolving to the current latest compatible release.

- [ ] **Step 9: Run package clean-install smoke**

```bash
rm -rf /tmp/noqlen-smoke
python -m venv /tmp/noqlen-smoke
/tmp/noqlen-smoke/bin/python -m pip install dist/*.whl
/tmp/noqlen-smoke/bin/python -c "import beetsplug.noqlenmeta"
/tmp/noqlen-smoke/bin/beet -p noqlenmeta nm --help
```

- [ ] **Step 10: Inspect final scope**

```bash
git status --short
git diff --check a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
git diff --stat a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
git grep -n "beetsplug.lastgenre" -- beetsplug tests
```

Confirm no CAA/artwork/BPM/version-bump implementation and no runtime LastGenre dependency entered the branch.

- [ ] **Step 11: Commit Task 6**

```bash
git add beetsplug/noqlenmeta/semantic_media.py beetsplug/noqlenmeta/file_sync.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_media.py tests/test_file_sync.py tests/test_v2_foundation_command.py README.md site-docs/reference/configuration.md site-docs/concepts/preview-apply-write.md
git commit -m "feat: complete semantic enrichment integration"
```

- [ ] **Step 12: Record PR-readiness evidence**

Record exact `HEAD`, full CI-equivalent result, both beets compatibility results, package smoke result, and diff summary. PR base is `docs/v2-enrichment-design`. Do not merge or release without a new explicit user authorization after fresh CI/review inspection.

---

## Self-Review Coverage

- Classifier + unique categories -> Task 1.
- Genres across Track/Release/Artist -> Tasks 3-5.
- Structured/community styles -> Tasks 1, 4-6.
- Hybrid moods + default one -> Tasks 1, 3-6.
- Recording -> Work lyric languages -> Tasks 3, 5, 6.
- Contextual artist languages -> Tasks 5-6.
- Artist area/country -> Tasks 3, 5, 6.
- Command cache/multi-scope specs -> Tasks 2-5.
- Field-aware Last.fm fallback -> Tasks 4-5.
- Explicit outcome states -> Task 5.
- Import/library parity -> Task 5.
- Lossless file sync + actual reopen verification -> Task 6.
- CI/package/beets compatibility -> Task 6.
- Artwork/BPM/version bump stay out of scope -> Global Constraints + Task 6 scope check.

No task authorizes merge or release.
