# Noqlen Meta v2 Semantic Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Semantic Enrichment phase so exact MusicBrainz identities produce useful zero-credential genres, moods, lyric languages, artist languages, and artist geography, while Discogs and Last.fm improve coverage without weakening deterministic resolution or write safety.

**Architecture:** Extend the Foundation's `RELEASE`, `TRACK`, and `ARTIST` scopes. Providers emit structured metadata and normalized semantic evidence; pure resolvers choose canonical values; only the existing change-plan/application layer may mutate beets or media files. Use one command-lifetime exact-entity cache and field-aware Last.fm fallback so data already collected for one field is reused by every compatible field.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, mediafile/mutagen through beets, requests, pytest, ruff, MkDocs, existing Noqlen provider/change-plan/file-sync infrastructure.

## Global Constraints

- Work on `feat/semantic-enrichment`, whose semantic spec commit is `a857b1cd5b88d39e2e1e7393b455645e1867c532` and whose v2 Foundation base is `f651dafc3691d33287b2dca38f960a4c5b533f42`.
- Design authority: `docs/superpowers/specs/2026-08-10-semantic-enrichment-design.md`.
- MusicBrainz is the zero-credential semantic backbone and must use exact MBIDs already selected/stored by beets/Noqlen. Do not add fuzzy MusicBrainz identity search.
- Discogs remains opt-in and is the structured style authority.
- Last.fm remains opt-in and uses field-aware Track -> Release -> Artist fallback.
- `moods.max_moods` defaults to `1` and accepts only integer values from `1` through `10`.
- Every accepted community term has exactly one primary category: `GENRE`, `STYLE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, or `NOISE`.
- Unknown community tags are never persisted automatically.
- `lyrics_languages` and `artist_languages` persist canonical three-letter language codes.
- `artist_languages` is derived only from identified Works in the current target. Do not crawl an artist's full catalogue.
- `artist_countries` is geographic identification/origin, not citizenship. Never infer it from language, artist name, release country, title script, or geographic-name string matching.
- Provider/network failures are local when safe. Structural plan/file-safety failures remain blocking.
- Do not add a persistent API cache or request-budget setting.
- `--write` must not add provider calls or collection work.
- Importer and existing-library paths share contexts, evidence, classification, resolution, and semantics.
- Preserve identity/AcoustID behavior, Genre Foundation ranking, `genres.num_genres`, `genres.promote_styles`, and legacy scalar `style` fallback.
- Do not implement Cover Art Archive, artwork download/embed, BPM, `[audio]`, local ML mood analysis, or a release/version bump.
- Do not add another mandatory beets plugin dependency.
- CI compatibility targets remain beets `2.12.0` and latest beets `<3`.

---

## File Map

### Create

- `beetsplug/noqlenmeta/semantic_tags.py` — semantic categories, canonical tag evidence, deterministic classifier, compact mood/style/origin/noise vocabularies.
- `beetsplug/noqlenmeta/semantic_resolution.py` — pure style and mood resolution.
- `beetsplug/noqlenmeta/provider_cache.py` — command-lifetime exact-entity payload and negative cache.
- `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py` — exact Recording/Work/Artist/Area semantic lookups and normalization.
- `beetsplug/noqlenmeta/semantic_enrichment.py` — shared semantic orchestration and explicit field outcomes.
- `beetsplug/noqlenmeta/semantic_media.py` — registered semantic MediaFile descriptors and lossless mapping capability checks.
- `tests/test_semantic_tags.py`
- `tests/test_semantic_resolution.py`
- `tests/test_provider_cache.py`
- `tests/test_musicbrainz_semantic.py`
- `tests/test_semantic_enrichment.py`
- `tests/test_semantic_media.py`

### Modify

- `beetsplug/noqlenmeta/domain.py`
- `beetsplug/noqlenmeta/configuration.py`
- `beetsplug/noqlenmeta/providers/specs.py`
- `beetsplug/noqlenmeta/providers/musicbrainz.py`
- `beetsplug/noqlenmeta/providers/lastfm.py`
- `beetsplug/noqlenmeta/providers/discogs.py`
- `beetsplug/noqlenmeta/genre_pipeline.py`
- `beetsplug/noqlenmeta/integration.py`
- `beetsplug/noqlenmeta/track_integration.py`
- `beetsplug/noqlenmeta/library_integration.py`
- `beetsplug/noqlenmeta/file_sync.py`
- `beetsplug/noqlenmeta/__init__.py`
- `tests/test_provider_specs.py`
- `tests/test_musicbrainz_provider.py`
- `tests/test_lastfm_provider.py`
- `tests/test_discogs_provider.py`
- `tests/test_genre_pipeline.py`
- `tests/test_genre_resolution.py`
- `tests/test_file_sync.py`
- `tests/test_v2_foundation_command.py`
- `tests/test_beets_integration.py`
- `README.md`
- `site-docs/reference/configuration.md`
- `site-docs/concepts/preview-apply-write.md`

---

### Task 1: Semantic classifier, mood/style resolution, and config

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_tags.py`
- Create: `beetsplug/noqlenmeta/semantic_resolution.py`
- Modify: `beetsplug/noqlenmeta/domain.py`
- Modify: `beetsplug/noqlenmeta/configuration.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Test: `tests/test_semantic_tags.py`
- Test: `tests/test_semantic_resolution.py`
- Test: `tests/test_v2_foundation_command.py`

**Interfaces:**

```python
class SemanticCategory(Enum):
    GENRE = "genre"
    STYLE = "style"
    MOOD = "mood"
    ORIGIN = "origin"
    DESCRIPTOR = "descriptor"
    NOISE = "noise"

@dataclass(frozen=True, slots=True)
class SemanticTagEvidence:
    term: str
    category: SemanticCategory
    provider: str
    scope: ProviderScope
    confidence: float
    source_id: str
    source_url: str | None = None
    weight: int | None = None
    raw_tag: str | None = None

@dataclass(frozen=True, slots=True)
class SemanticEvidenceBundle:
    metadata: tuple[MetadataCandidate, ...] = ()
    genres: tuple[GenreEvidence, ...] = ()
    tags: tuple[SemanticTagEvidence, ...] = ()

def classify_semantic_tag(
    raw_tag: str,
    *,
    provider: str,
    scope: ProviderScope,
    confidence: float,
    source_id: str,
    source_url: str | None = None,
    weight: int | None = None,
) -> SemanticTagEvidence | None: ...

def resolve_styles(
    structured: Sequence[MetadataCandidate],
    community: Sequence[SemanticTagEvidence],
) -> tuple[str, ...]: ...

def resolve_moods(
    evidence: Sequence[SemanticTagEvidence],
    *,
    max_moods: int,
) -> tuple[str, ...]: ...
```

The function bodies above are signatures only; implementation steps below define their required behavior.

- [ ] **Step 1: Write RED classifier tests**

Create `tests/test_semantic_tags.py` with a local helper that constructs evidence and tests these exact classifications:

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

Also assert blank and unknown tags return `None`, Genre Foundation classification is reused for genre terms, and one raw tag yields only one category.

Run:

```bash
pytest -q tests/test_semantic_tags.py
```

Expected: FAIL because the semantic classifier does not exist yet.

- [ ] **Step 2: Implement the deterministic classifier**

Normalize with NFKC + casefold + collapsed whitespace. Classification precedence is fixed:

```text
NOISE
-> existing Genre Foundation taxonomy
-> STYLE allowlist
-> MOOD taxonomy/aliases
-> ORIGIN allowlist
-> DESCRIPTOR allowlist
-> unknown => None
```

Keep the initial non-genre vocabularies compact. Include only reviewed canonical terms and aliases required by the design/tests; do not import a large external tag list wholesale.

- [ ] **Step 3: Write RED resolver tests**

Required assertions:

```python
assert resolve_moods(
    (
        mood_evidence("Melancholic", "musicbrainz", ProviderScope.TRACK, 8),
        mood_evidence("Dreamy", "musicbrainz", ProviderScope.TRACK, 7),
    ),
    max_moods=1,
) == ("Melancholic",)

assert resolve_moods(
    (
        mood_evidence("Dreamy", "musicbrainz", ProviderScope.RELEASE, 7),
        mood_evidence("Dreamy", "lastfm", ProviderScope.RELEASE, 70),
        mood_evidence("Melancholic", "musicbrainz", ProviderScope.RELEASE, 8),
    ),
    max_moods=1,
) == ("Dreamy",)

assert resolve_styles(
    (
        MetadataCandidate(
            "styles",
            ("Progressive Metal", "Technical Death Metal"),
            "discogs",
            0.95,
            "discogs-release-1",
        ),
    ),
    (
        style_evidence("Alternative Metal", "lastfm", ProviderScope.RELEASE, 80),
    ),
) == ("Progressive Metal", "Technical Death Metal")
```

The test module must define `mood_evidence()` and `style_evidence()` as explicit constructors for `SemanticTagEvidence`; do not hide policy in test fixtures.

Run:

```bash
pytest -q tests/test_semantic_resolution.py
```

Expected: FAIL because the resolvers do not exist yet.

- [ ] **Step 4: Implement pure resolvers**

Filter invalid/unrecognized evidence first. Rank using ordered policy components rather than a universal summed score:

```text
eligible evidence
-> scope relevance
-> distinct-provider corroboration
-> evidence strength
-> native provider weight
-> stable input/canonical ordering
```

For `styles`, eligible structured Discogs styles win as the preserved ordered tuple; community `STYLE` evidence is fallback coverage when structured styles are absent.

- [ ] **Step 5: Add `moods.max_moods` config validation**

Add to `default_config()`:

```yaml
moods:
  max_moods: 1
```

Add command-level tests proving integer `1` and `3` are accepted and values `0`, `11`, `True`, and `"1"` are rejected before any provider call.

- [ ] **Step 6: Verify Task 1**

```bash
pytest -q tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
ruff check beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/configuration.py tests/test_semantic_tags.py tests/test_semantic_resolution.py
```

- [ ] **Step 7: Commit Task 1**

```bash
git add beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/configuration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
git commit -m "feat: add semantic tag classification"
```

---

### Task 2: Command cache and multi-scope provider capabilities

**Files:**
- Create: `beetsplug/noqlenmeta/provider_cache.py`
- Modify: `beetsplug/noqlenmeta/providers/specs.py`
- Test: `tests/test_provider_cache.py`
- Test: `tests/test_provider_specs.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class EntityCacheKey:
    provider: str
    entity_type: str
    entity_id: str

class CommandEntityCache:
    def get_or_fetch(
        self,
        key: EntityCacheKey,
        fetcher: Callable[[], Mapping[str, object] | None],
    ) -> Mapping[str, object] | None: ...
```

- [ ] **Step 1: Write RED cache tests**

Test three observable behaviors with integer call counters:

1. Two identical successful lookups invoke the fetcher once.
2. Two identical definitive `None` lookups invoke the fetcher once.
3. A first fetcher raising `RequestException` is not cached; a second fetcher for the same key runs and can succeed.

Run:

```bash
pytest -q tests/test_provider_cache.py
```

Expected: FAIL because `provider_cache.py` does not exist.

- [ ] **Step 2: Implement the cache**

Use exactly one payload dictionary and one negative-cache set. Let fetcher exceptions propagate without modifying either collection. Validate non-empty canonical strings in `EntityCacheKey`.

- [ ] **Step 3: Expand provider specs without name collisions**

Keep release specs and add distinct `(name, scope)` entries:

```text
musicbrainz / RELEASE
musicbrainz / TRACK
musicbrainz / ARTIST
lastfm / RELEASE
lastfm / TRACK
lastfm / ARTIST
```

Capabilities after this phase:

```text
MusicBrainz TRACK: genres, moods, lyrics_languages
MusicBrainz ARTIST: genres, moods, artist_countries, artist_areas
Last.fm TRACK: genres, styles, moods
Last.fm RELEASE: genres, styles, moods
Last.fm ARTIST: genres, styles, moods
```

`artist_languages` is derived by orchestration and is not advertised as an Artist-provider lookup field.

- [ ] **Step 4: Add registry regression tests**

Assert all six keys coexist and that existing release/track registries still return the expected specs. Search and update any production caller that retrieves a provider only by `name` when scope is required.

- [ ] **Step 5: Verify Task 2**

```bash
pytest -q tests/test_provider_cache.py tests/test_provider_specs.py
ruff check beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py tests/test_provider_specs.py
```

- [ ] **Step 6: Commit Task 2**

```bash
git add beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py tests/test_provider_specs.py
git commit -m "refactor: add semantic provider cache scopes"
```

---

### Task 3: MusicBrainz semantic evidence from exact entities

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/musicbrainz.py`
- Create: `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py`
- Modify: `beetsplug/noqlenmeta/genre_pipeline.py`
- Test: `tests/test_musicbrainz_provider.py`
- Test: `tests/test_musicbrainz_semantic.py`
- Test: `tests/test_genre_pipeline.py`
- Test: `tests/test_genre_resolution.py`

**Interfaces:**

```python
class MusicBrainzSemanticClient:
    def release(self, mbid: str) -> Mapping[str, object] | None: ...
    def recording(self, mbid: str) -> Mapping[str, object] | None: ...
    def work(self, mbid: str) -> Mapping[str, object] | None: ...
    def artist(self, mbid: str) -> Mapping[str, object] | None: ...
    def area(self, mbid: str) -> Mapping[str, object] | None: ...

class MusicBrainzTrackProvider:
    name = "musicbrainz"
    def get_semantic_evidence(
        self,
        context: TrackEnrichmentContext,
    ) -> SemanticEvidenceBundle: ...

class MusicBrainzArtistProvider:
    name = "musicbrainz"
    def get_semantic_evidence(
        self,
        context: ArtistEnrichmentContext,
    ) -> SemanticEvidenceBundle: ...
```

Existing `MusicBrainzProvider.get_candidates()` remains available for ordinary release fields; add a release semantic-evidence method instead of breaking that contract.

- [ ] **Step 1: Write RED release union-lookup tests**

Inject a fetch function that records requested includes. For enabled release semantics, assert one release request contains the union of existing and semantic includes needed by implementation, including existing `labels`/`media` and semantic `genres`/`tags`. Preserve exact response-MBID validation.

- [ ] **Step 2: Write RED Recording -> Work language tests**

Use fixed UUID constants in the test module. Cover:

- one Recording linked to two Works returning `kor`, `eng`, `kor` -> one candidate `("kor", "eng")`;
- two tracks linked to the same Work -> one Work fetch via `CommandEntityCache`;
- Work with absent language -> no `lyrics_languages` candidate;
- explicit instrumental/no-lyrics Work -> no fabricated language;
- malformed language token -> ignored, not translated or guessed.

Run:

```bash
pytest -q tests/test_musicbrainz_semantic.py
```

Expected: FAIL because the semantic MusicBrainz adapter does not exist.

- [ ] **Step 3: Write RED genre/tag scope tests**

Representative Recording payload must include:

```python
{
    "id": RECORDING_MBID,
    "genres": [{"name": "k-pop", "count": 9}],
    "tags": [
        {"name": "dreamy", "count": 8},
        {"name": "seen live", "count": 2},
    ],
    "relations": [],
}
```

Assert `K-pop` becomes Track-scope direct genre evidence, `Dreamy` becomes Track-scope mood evidence, and `seen live` never becomes a metadata value. Add equivalent Release- and Artist-scope cases.

- [ ] **Step 4: Write RED artist geography tests**

Cover these exact cases:

```text
main area = Salvador; structural Area ancestry reaches Brazil -> area Salvador + country Brazil
main area = trustworthy city; country ancestry unavailable -> area only
main area absent; trustworthy begin-area structurally resolves -> controlled fallback allowed
main area present; conflicting begin-area -> main area wins
```

No test may derive country by parsing the area name.

- [ ] **Step 5: Implement cached exact lookups**

Use keys:

```text
musicbrainz/release/<release MBID>
musicbrainz/recording/<recording MBID>
musicbrainz/work/<work MBID>
musicbrainz/artist/<artist MBID>
musicbrainz/area/<area MBID>
```

Every payload that contains an `id` must canonicalize to the requested MBID. Mismatch is `ProviderError`, not negative cache.

- [ ] **Step 6: Normalize MusicBrainz semantic data**

Rules:

- direct MusicBrainz genres -> existing `GenreEvidence` direct kind at entity scope;
- MusicBrainz community tags -> `classify_semantic_tag()`;
- classified community `GENRE` -> weaker community `GenreEvidence`;
- classified `MOOD`/`STYLE` -> semantic tag evidence;
- classified `ORIGIN` never creates geographic metadata;
- Work language accepts only lowercase/normalized three-letter codes and preserves provider order with deduplication;
- area/country comes only from MusicBrainz Area structure/type/ISO/ancestry.

- [ ] **Step 7: Integrate new genre scopes without changing ranking**

Pass eligible Track/Release/Artist MusicBrainz genre evidence into the existing specialized resolver. Preserve filtering before scope preference and distinct-provider corroboration by provider identity, not row count.

- [ ] **Step 8: Verify Task 3**

```bash
pytest -q tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py beetsplug/noqlenmeta/genre_pipeline.py tests/test_musicbrainz_semantic.py
```

- [ ] **Step 9: Commit Task 3**

```bash
git add beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py beetsplug/noqlenmeta/genre_pipeline.py tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add MusicBrainz semantic evidence"
```

---

### Task 4: Last.fm lazy multi-scope fallback and Discogs style authority

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/lastfm.py`
- Modify: `beetsplug/noqlenmeta/providers/discogs.py`
- Modify: `beetsplug/noqlenmeta/semantic_resolution.py`
- Test: `tests/test_lastfm_provider.py`
- Test: `tests/test_discogs_provider.py`
- Test: `tests/test_semantic_resolution.py`
- Test: `tests/test_genre_pipeline.py`

- [ ] **Step 1: Write RED Last.fm scope tests**

Add separate tests for Track, Release, and Artist top-tag normalization. Each accepted tag must preserve provider, scope, source identity, native weight, and canonical category. Unknown/noise tags must not become metadata.

- [ ] **Step 2: Write RED field-aware fallback tests**

Use explicit call counters and assert:

```text
Track resolves genre + mood -> Release calls 0; Artist calls 0
Track resolves genre only -> Release may run for mood
Release then resolves mood -> Artist calls 0
Track/Release remain insufficient -> Artist may run for unresolved fields
```

Genre being resolved must not prevent a later fallback call needed only for mood or style.

- [ ] **Step 3: Implement scoped Last.fm collection**

Reuse the existing Last.fm authenticated request boundary and existing error semantics. Prefer a known MBID when the endpoint supports it; otherwise use exact already-identified context strings. Do not add a Last.fm identity-search/disambiguation subsystem.

Route every returned community tag through `classify_semantic_tag()` before it can influence genre/style/mood.

- [ ] **Step 4: Preserve structured Discogs styles**

Keep Discogs release `styles` as structured ordered metadata. Do not require those values to pass the community style allowlist. Preserve existing independent style->genre promotion only when `genres.promote_styles` is enabled and the genre taxonomy recognizes the style.

- [ ] **Step 5: Verify Task 4**

```bash
pytest -q tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/providers/discogs.py beetsplug/noqlenmeta/semantic_resolution.py
```

- [ ] **Step 6: Commit Task 4**

```bash
git add beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/providers/discogs.py beetsplug/noqlenmeta/semantic_resolution.py tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add scoped semantic fallback"
```

---

### Task 5: Shared orchestration, derived artist languages, parity, and outcome reporting

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_enrichment.py`
- Modify: `beetsplug/noqlenmeta/integration.py`
- Modify: `beetsplug/noqlenmeta/track_integration.py`
- Modify: `beetsplug/noqlenmeta/library_integration.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Test: `tests/test_semantic_enrichment.py`
- Test: `tests/test_v2_foundation_command.py`
- Test: `tests/test_beets_integration.py`

**Interfaces:**

```python
class SemanticFieldStatus(Enum):
    RESOLVED = "resolved"
    NO_EVIDENCE = "no-evidence"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"
    BLOCKED = "blocked"

@dataclass(frozen=True, slots=True)
class SemanticFieldOutcome:
    field: str
    status: SemanticFieldStatus
    value: MetadataValue | None
    provenance: tuple[str, ...]
    reason: str

@dataclass(frozen=True, slots=True)
class SemanticEnrichmentResult:
    metadata: tuple[MetadataCandidate, ...]
    outcomes: tuple[SemanticFieldOutcome, ...]

def derive_artist_languages(
    track_languages: Sequence[tuple[int, tuple[str, ...]]],
) -> tuple[str, ...]: ...
```

`track_languages` uses credited-artist order index plus already-resolved current-target Work languages; it never triggers network work itself.

- [ ] **Step 1: Write RED field-gating tests**

With only `genres` enabled, assert Work-language fetch count is zero and no mood/language outcome is emitted. Repeat with moods disabled and lyric languages enabled to prove only required capabilities are requested.

- [ ] **Step 2: Write RED artist-language/credit-order tests**

Use this exact input and expected output:

```python
track_languages = (
    (1, ("kor",)),
    (1, ("kor", "eng")),
    (2, ("jpn",)),
)
assert derive_artist_languages(track_languages) == ("kor", "eng", "jpn")
```

Add artist country/area aggregation tests preserving first credit order and deduplicating repeated values.

- [ ] **Step 3: Write RED outcome-state tests**

Assert these distinctions:

```text
Work exists but no usable language -> NO_EVIDENCE
Work network lookup fails -> UNAVAILABLE
eligible evidence has no deterministic winner -> CONFLICT
lossless target mapping unavailable -> BLOCKED
safe selected value -> RESOLVED
```

One field/provider failure must not erase unrelated successful metadata candidates.

- [ ] **Step 4: Implement one shared `collect_semantic_enrichment()` flow**

Execution order is fixed:

```text
compute enabled semantic fields
-> build exact release/track/artist contexts from existing IDs
-> create/reuse one CommandEntityCache for command execution
-> collect MusicBrainz evidence only for required scopes/capabilities
-> combine configured Discogs structured evidence
-> resolve currently resolvable fields
-> if Last.fm enabled, query Track -> Release -> Artist only for still-unresolved community fields
-> resolve genres/styles/moods
-> derive artist_languages from current-target Work languages
-> aggregate artist areas/countries in credit order
-> return candidates + explicit outcomes
```

No DB or file write is allowed inside `collect_semantic_enrichment()`.

- [ ] **Step 5: Wire existing-library command path**

Use `context_from_library_album()` / `context_from_library_item()` plus new Artist-context extraction in `library_integration.py`. Keep Foundation command-wide file preflight before DB mutation when `--write` is requested.

- [ ] **Step 6: Wire importer path without re-identification**

In `_import_task_choice`, reuse the selected `AlbumInfo`/`TrackInfo` MBIDs already exposed through `integration.py` and `track_integration.py`. Both release and track importer branches must call the same semantic orchestration/resolvers used by existing-library targets.

- [ ] **Step 7: Add parity tests**

For one deterministic selected album/track fixture, assert importer and library flows resolve identical canonical values for:

```text
genres
styles
moods
lyrics_languages
artist_languages
artist_countries
artist_areas
```

- [ ] **Step 8: Add concise normal preview/outcome tests**

Normal output must show resolved field/value and useful provenance, plus explicit `no-evidence`, `unavailable`, `conflict`, or `blocked` when relevant. Rejected raw tags such as `seen live` must not appear in normal output.

Preserve Foundation output phases: database preview, file preview, then actual application result.

- [ ] **Step 9: Verify Task 5**

```bash
pytest -q tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
ruff check beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/integration.py beetsplug/noqlenmeta/track_integration.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_enrichment.py
```

- [ ] **Step 10: Commit Task 5**

```bash
git add beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/integration.py beetsplug/noqlenmeta/track_integration.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
git commit -m "feat: integrate semantic enrichment pipeline"
```

---

### Task 6: Lossless semantic file sync, docs, and final verification

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

Official beets exposes plugin-added MediaFile fields through `BeetsPlugin.add_media_field()`. Use that mechanism; do not bypass MediaFile with direct Mutagen writes.

- [ ] **Step 1: Write RED real-file round-trip tests**

Register Noqlen semantic media fields with these logical storage purposes:

```text
styles
moods
lyrics_languages
artist_languages
artist_countries
artist_areas
```

For each mapping enabled in production, the test must write an ordered multivalue tuple to a copied real media fixture, reopen it through `MediaFile`, and assert the same values/order are observed. Include values containing spaces and hyphens. A format/field combination that cannot round-trip losslessly must not be enabled in the mapping table.

Run:

```bash
pytest -q tests/test_semantic_media.py tests/test_file_sync.py
```

Expected: FAIL because semantic descriptors/mappings do not exist.

- [ ] **Step 2: Implement registered semantic media fields**

Create descriptors in `semantic_media.py` and register them from `NoqlenMetaPlugin.__init__()` using `add_media_field`. Keep canonical DB field names unchanged. The descriptor/storage choice must pass the Step 1 observable round-trip test before the field is added to `file_sync` mappings.

Do not serialize multivalue tuples into an ambiguous human separator merely to avoid a blocker.

- [ ] **Step 3: Extend Foundation file-sync mapping**

Map only semantic fields whose registered MediaFile descriptor is lossless for the target. Preserve existing global preflight, candidate-save verification, stale source checks, recovery artifact behavior, and final reopen/read verification. Unsupported lossless mappings remain `blocked` before DB mutation under `--apply --write`.

- [ ] **Step 4: Add command-level observable write test**

Prepare a temporary real media file and deterministic semantic candidates. Run:

```text
beet nm --apply --write --all
```

through the test invocation helper, then reopen both library DB and MediaFile. Assert DB and file contain the same semantic values. Do not assert only `FileSyncResult` flags.

- [ ] **Step 5: Update docs with exact implemented behavior**

Document:

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

Also document exact-ID MusicBrainz semantics, Discogs structured styles, Last.fm lazy fallback, three-letter language fields, contextual artist languages, geographic-identification semantics, the semantic media fields actually supported, `--write` not triggering collection, and Artwork/BPM remaining for the next phase.

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

- [ ] **Step 7: Run exact CI-equivalent local checks**

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

- [ ] **Step 8: Run exact beets compatibility suites**

Minimum lane:

```bash
python -m pip install -e ".[dev]" "beets==2.12.0"
pytest \
  tests/test_plugin_loads.py \
  tests/test_beets_integration.py \
  tests/test_library_cli.py \
  tests/identity/test_library_identity_command.py \
  tests/identity/test_identity_tag_command.py
```

Latest-below-3 lane in a clean environment:

```bash
python -m pip install -e ".[dev]" "beets<3"
pytest \
  tests/test_plugin_loads.py \
  tests/test_beets_integration.py \
  tests/test_library_cli.py \
  tests/identity/test_library_identity_command.py \
  tests/identity/test_identity_tag_command.py
```

Do not reuse one environment for both version assertions without reinstalling the intended beets constraint.

- [ ] **Step 9: Run package clean-install smoke**

```bash
rm -rf /tmp/noqlen-smoke
python -m venv /tmp/noqlen-smoke
/tmp/noqlen-smoke/bin/python -m pip install dist/*.whl
/tmp/noqlen-smoke/bin/python -c "import beetsplug.noqlenmeta"
/tmp/noqlen-smoke/bin/beet -p noqlenmeta nm --help
```

- [ ] **Step 10: Inspect final branch diff and scope**

```bash
git status --short
git diff --check a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
git diff --stat a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
git grep -n "beetsplug.lastgenre" -- beetsplug tests
```

Confirm there is no Artwork/CAA/BPM/version-bump implementation and no runtime dependency on beets LastGenre.

- [ ] **Step 11: Commit Task 6**

```bash
git add beetsplug/noqlenmeta/semantic_media.py beetsplug/noqlenmeta/file_sync.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_media.py tests/test_file_sync.py tests/test_v2_foundation_command.py README.md site-docs/reference/configuration.md site-docs/concepts/preview-apply-write.md
git commit -m "feat: complete semantic enrichment integration"
```

- [ ] **Step 12: Record PR-readiness evidence**

Record the exact current `HEAD`, full CI-equivalent result, both beets compatibility results, package smoke result, and final diff summary. Open the PR against `docs/v2-enrichment-design`; do not retarget to `main`. Do not merge without a new explicit user authorization after fresh CI/review inspection.

---

## Self-Review Coverage Matrix

- Semantic classification and unique categories -> Task 1.
- Genre multi-scope evidence -> Tasks 3-5.
- Structured/community styles -> Tasks 1, 4-6.
- Hybrid moods + default one -> Tasks 1, 3-6.
- Recording -> Work lyric languages -> Tasks 3, 5, 6.
- Contextual artist languages -> Tasks 5, 6.
- Artist main-area/country -> Tasks 3, 5, 6.
- Multi-scope provider specs/cache -> Tasks 2-5.
- Field-aware Last.fm fallback -> Tasks 4-5.
- Explicit no-evidence/unavailable/conflict/blocked outcomes -> Task 5.
- Import/existing-library parity -> Task 5.
- Lossless file sync + observable reopen verification -> Task 6.
- CI/package/beets compatibility -> Task 6.
- Artwork/BPM/version bump remain out of scope -> Global Constraints + Task 6 diff inspection.

No task authorizes merge or release.
