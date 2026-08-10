# Noqlen Meta v2 Semantic Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Semantic Enrichment phase so exact MusicBrainz identities provide useful zero-credential genres, moods, lyric languages, artist languages, and artist geography, while Discogs and Last.fm improve coverage without weakening Noqlen's deterministic resolution and write-safety model.

**Architecture:** Extend the Foundation's `RELEASE`, `TRACK`, and `ARTIST` provider scopes instead of creating field-specific mini-systems. Providers produce structured metadata plus normalized semantic evidence; pure classifiers/resolvers select canonical values; the existing change-plan/application pipeline remains the only mutation path. Use exact-entity command-lifetime caching and lazy Last.fm fallback so one entity lookup can feed every enabled semantic field.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, mediafile/mutagen through beets, requests, pytest, ruff, existing Noqlen provider/change-plan/file-sync infrastructure.

## Global Constraints

- Base branch for this work: `feat/semantic-enrichment`, created from `docs/v2-enrichment-design` after V2 Foundation + Genre Foundation merge commit `f651dafc3691d33287b2dca38f960a4c5b533f42`.
- Approved design: `docs/superpowers/specs/2026-08-10-semantic-enrichment-design.md`.
- MusicBrainz is the zero-credential semantic backbone and must use exact existing MBIDs; do not add fuzzy MusicBrainz identity search.
- Discogs remains opt-in and is the structured style authority.
- Last.fm remains opt-in and contributes community evidence with lazy Track -> Release -> Artist fallback.
- `moods.max_moods` defaults to `1`; accept only integer values `1..10`.
- Every canonical community term has one primary category: `GENRE`, `STYLE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, or `NOISE`.
- Unknown/raw community tags are never persisted automatically.
- `lyrics_languages` and `artist_languages` persist canonical three-letter MusicBrainz language codes, not translated names.
- `artist_languages` is derived only from identified Works in the current target; never crawl the artist's full catalogue.
- `artist_countries` means trustworthy geographic identification/origin, not citizenship; never infer it from language, title script, release country, artist name, or geographic-name string matching.
- Missing evidence is preferable to fabricated metadata.
- Provider/network failures remain local when safe; structural plan/write failures remain blocking.
- No persistent API cache and no arbitrary request-budget setting in this phase.
- `--write` authorizes only already-planned file mutations and must never trigger additional provider work.
- Importer and existing-library paths must share context, evidence, classification, resolution, and field semantics.
- Preserve identity, AcoustID, existing genre ranking, `genres.num_genres`, `genres.promote_styles`, and legacy `style` migration behavior.
- Do not implement Cover Art Archive, artwork sidecars/embedding, BPM providers/local analysis, `[audio]`, local ML mood classification, or a release/version bump in this plan.
- Do not add another mandatory beets plugin dependency.
- Keep production behavior compatible with beets 2.12 and the latest beets `<3` CI lane.

---

## File Structure

### New semantic core

- Create `beetsplug/noqlenmeta/semantic_tags.py` — semantic categories, normalized community-tag evidence, classifier, aliases, and bundled mood/style/origin/noise vocabulary.
- Create `beetsplug/noqlenmeta/semantic_resolution.py` — pure style/mood selection and semantic result types; genre selection remains in the existing specialized genre resolver.
- Create `beetsplug/noqlenmeta/provider_cache.py` — command-lifetime exact-entity response/negative cache; transient exceptions are not cached.

### Provider changes

- Modify `beetsplug/noqlenmeta/providers/specs.py` — declare MusicBrainz and Last.fm capabilities at release/track/artist scopes.
- Modify `beetsplug/noqlenmeta/providers/musicbrainz.py` — expand release lookup to unioned semantic includes and emit release semantic evidence.
- Create `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py` — exact Recording, Work, Artist, and Area lookups plus normalized track/artist/language/geographic semantic output.
- Modify `beetsplug/noqlenmeta/providers/lastfm.py` — add exact-context Track/Release/Artist top-tag collection without independent fuzzy identity search.
- Modify `beetsplug/noqlenmeta/providers/discogs.py` only where needed to expose the already-structured `styles`/`genres` cleanly to semantic orchestration; do not add track/artist crawling.

### Orchestration/application

- Modify `beetsplug/noqlenmeta/domain.py` — add semantic bundle/result values only if they are provider-independent domain objects.
- Modify `beetsplug/noqlenmeta/genre_pipeline.py` — accept MusicBrainz/Last.fm genre evidence at track/release/artist scopes while preserving current ranking behavior.
- Modify `beetsplug/noqlenmeta/__init__.py` — configuration, enabled-field planning, scoped provider registration/collection, lazy fallback, shared cache lifetime, preview/outcome reporting, and existing-library orchestration.
- Modify the existing importer enrichment module(s) used by Noqlen Meta — route importer targets through the same semantic collection/resolution entry point; do not duplicate classifier/resolver logic.
- Modify `beetsplug/noqlenmeta/file_sync.py` — add only lossless semantic media mappings; unsupported mappings remain explicit blockers.

### Tests/docs

- Create `tests/test_semantic_tags.py`.
- Create `tests/test_semantic_resolution.py`.
- Create `tests/test_provider_cache.py`.
- Create `tests/test_musicbrainz_semantic.py`.
- Extend `tests/test_musicbrainz_provider.py`.
- Extend `tests/test_lastfm_provider.py`.
- Extend `tests/test_genre_pipeline.py` / existing genre-resolution tests.
- Extend `tests/test_v2_foundation_command.py` for command/application behavior.
- Extend importer integration tests in the existing importer test module(s).
- Extend the real-media-file tests that currently verify `--apply --write` observable outcomes.
- Modify `README.md`, `site-docs/reference/configuration.md`, `site-docs/concepts/preview-apply-write.md`, and the relevant provider/reference page(s) to document the implemented semantic behavior truthfully.

---

### Task 1: Semantic classifier, mood/style evidence, and configuration

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_tags.py`
- Create: `beetsplug/noqlenmeta/semantic_resolution.py`
- Modify: `beetsplug/noqlenmeta/domain.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Test: `tests/test_semantic_tags.py`
- Test: `tests/test_semantic_resolution.py`
- Test: `tests/test_v2_foundation_command.py`

**Interfaces:**
- Produces:
  - `SemanticCategory(Enum)` with `GENRE`, `STYLE`, `MOOD`, `ORIGIN`, `DESCRIPTOR`, `NOISE`.
  - `SemanticTagEvidence(term: str, category: SemanticCategory, provider: str, scope: ProviderScope, confidence: float, source_id: str, source_url: str | None = None, weight: int | None = None, raw_tag: str | None = None)`.
  - `SemanticEvidenceBundle(metadata: tuple[MetadataCandidate, ...] = (), genres: tuple[GenreEvidence, ...] = (), tags: tuple[SemanticTagEvidence, ...] = ())`.
  - `classify_semantic_tag(raw_tag: str, *, provider: str, scope: ProviderScope, confidence: float, source_id: str, source_url: str | None = None, weight: int | None = None) -> SemanticTagEvidence | None`.
  - `resolve_styles(structured: Sequence[MetadataCandidate], community: Sequence[SemanticTagEvidence]) -> tuple[str, ...]`.
  - `resolve_moods(evidence: Sequence[SemanticTagEvidence], *, max_moods: int) -> tuple[str, ...]`.
  - `MoodSettings(max_moods: int)` validation through plugin configuration.
- Consumes: existing `ProviderScope`, `MetadataCandidate`, Genre Foundation taxonomy/classifier functions, and existing preserve/change-plan semantics.

- [ ] **Step 1: Write classifier tests before production code**

Create tests covering unique category assignment and representative aliases:

```python
@pytest.mark.parametrize(
    ("raw", "category", "term"),
    [
        ("melancholy", SemanticCategory.MOOD, "Melancholic"),
        ("melancholic", SemanticCategory.MOOD, "Melancholic"),
        ("dreamy", SemanticCategory.MOOD, "Dreamy"),
        ("atmospheric", SemanticCategory.MOOD, "Atmospheric"),
        ("progressive metal", SemanticCategory.STYLE, "Progressive Metal"),
        ("k-pop", SemanticCategory.GENRE, "K-pop"),
        ("korean", SemanticCategory.ORIGIN, "Korean"),
        ("seen live", SemanticCategory.NOISE, "Seen Live"),
    ],
)
def test_semantic_tag_has_one_canonical_category(raw, category, term):
    result = classify_semantic_tag(
        raw,
        provider="musicbrainz",
        scope=ProviderScope.TRACK,
        confidence=0.8,
        source_id="recording-1",
    )
    assert result is not None
    assert result.category is category
    assert result.term == term
```

Add explicit tests that blank/unknown tags return `None`, genre recognition reuses the bundled Noqlen genre taxonomy, and one raw tag never emits multiple evidence objects.

- [ ] **Step 2: Run the focused classifier tests and confirm RED**

Run:

```bash
pytest -q tests/test_semantic_tags.py
```

Expected: collection/import failure because `semantic_tags` does not exist yet.

- [ ] **Step 3: Implement the deterministic classifier with small bundled vocabularies**

Use normalization in this order:

```python
def _identity(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
```

Classification precedence must be explicit and single-valued:

```python
def classify_semantic_tag(...):
    key = _identity(raw_tag)
    if not key:
        return None
    if key in NOISE_TERMS:
        category, canonical = SemanticCategory.NOISE, NOISE_TERMS[key]
    elif (genre := classify_genre(raw_tag)) is not None:
        category, canonical = SemanticCategory.GENRE, genre
    elif key in STYLE_TERMS:
        category, canonical = SemanticCategory.STYLE, STYLE_TERMS[key]
    elif key in MOOD_TERMS:
        category, canonical = SemanticCategory.MOOD, MOOD_TERMS[key]
    elif key in ORIGIN_TERMS:
        category, canonical = SemanticCategory.ORIGIN, ORIGIN_TERMS[key]
    elif key in DESCRIPTOR_TERMS:
        category, canonical = SemanticCategory.DESCRIPTOR, DESCRIPTOR_TERMS[key]
    else:
        return None
    return SemanticTagEvidence(...)
```

Keep the first vocabulary deliberately compact. Include only terms represented in tests/spec examples plus a small useful canonical mood core; do not bulk-copy Forge or LastGenre lists without semantic review.

- [ ] **Step 4: Write mood/style resolver tests**

Cover:

```python
def test_default_mood_returns_only_best_value():
    evidence = (
        tag("Melancholic", provider="musicbrainz", scope=ProviderScope.TRACK, weight=8),
        tag("Dreamy", provider="musicbrainz", scope=ProviderScope.TRACK, weight=7),
    )
    assert resolve_moods(evidence, max_moods=1) == ("Melancholic",)


def test_cross_provider_corroboration_breaks_equivalent_tie():
    evidence = (
        tag("Dreamy", provider="musicbrainz", scope=ProviderScope.RELEASE, weight=7),
        tag("Dreamy", provider="lastfm", scope=ProviderScope.RELEASE, weight=70),
        tag("Melancholic", provider="musicbrainz", scope=ProviderScope.RELEASE, weight=8),
    )
    assert resolve_moods(evidence, max_moods=1) == ("Dreamy",)


def test_discogs_structured_styles_are_not_replaced_by_community_soup():
    structured = (
        MetadataCandidate("styles", ("Progressive Metal", "Technical Death Metal"), "discogs", 0.95, "1"),
    )
    community = (tag("Alternative Metal", provider="lastfm", category=SemanticCategory.STYLE),)
    assert resolve_styles(structured, community) == (
        "Progressive Metal",
        "Technical Death Metal",
    )
```

Also test stable ordering, provider-count corroboration, scope preference only after eligibility, deduplication, and `max_moods=3` without artificial padding.

- [ ] **Step 5: Run resolver tests and confirm RED**

```bash
pytest -q tests/test_semantic_resolution.py
```

- [ ] **Step 6: Implement the pure style/mood resolvers**

Do not create a universal numeric magic score. Express ranking as an ordered key whose components mirror the design:

```python
rank = (
    scope_rank,
    distinct_provider_count,
    evidence_strength,
    native_weight_or_zero,
    stable_order,
)
```

Filter ineligible/unrecognized evidence before rank computation. For styles, return structured Discogs values unchanged when eligible structured style evidence exists; use community `STYLE` evidence as fallback coverage rather than uncontrolled union.

- [ ] **Step 7: Add and validate `moods.max_moods`**

Default configuration:

```yaml
moods:
  max_moods: 1
```

Add command-level tests proving `0`, `11`, booleans, and strings are rejected before provider work, while `1` and `3` are accepted.

- [ ] **Step 8: Run focused tests**

```bash
pytest -q tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
ruff check beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py tests/test_semantic_tags.py tests/test_semantic_resolution.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 1**

```bash
git add beetsplug/noqlenmeta/semantic_tags.py beetsplug/noqlenmeta/semantic_resolution.py beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/__init__.py tests/test_semantic_tags.py tests/test_semantic_resolution.py tests/test_v2_foundation_command.py
git commit -m "feat: add semantic tag classification"
```

---

### Task 2: Command-lifetime exact-entity cache and provider scope declarations

**Files:**
- Create: `beetsplug/noqlenmeta/provider_cache.py`
- Modify: `beetsplug/noqlenmeta/providers/specs.py`
- Test: `tests/test_provider_cache.py`
- Extend: `tests/test_provider_specs.py` or the existing provider-spec registry tests

**Interfaces:**
- Produces:
  - `EntityCacheKey(provider: str, entity_type: str, entity_id: str)`.
  - `CommandEntityCache.get_or_fetch(key: EntityCacheKey, fetcher: Callable[[], Mapping[str, object] | None]) -> Mapping[str, object] | None`.
  - Separate MusicBrainz and Last.fm specs at `RELEASE`, `TRACK`, and `ARTIST` scopes using the same provider name and different `(name, scope)` registry keys.
- Consumes: existing multi-scope provider registry from Foundation.

- [ ] **Step 1: Write cache behavior tests**

Required cases:

```python
def test_successful_payload_is_fetched_once():
    calls = 0
    cache = CommandEntityCache()
    key = EntityCacheKey("musicbrainz", "artist", ARTIST_MBID)
    ...
    assert cache.get_or_fetch(key, fetcher) == payload
    assert cache.get_or_fetch(key, fetcher) == payload
    assert calls == 1


def test_not_found_is_negatively_cached():
    ...
    assert cache.get_or_fetch(key, fetcher) is None
    assert cache.get_or_fetch(key, fetcher) is None
    assert calls == 1


def test_transient_exception_is_not_cached():
    ...
    with pytest.raises(RequestException):
        cache.get_or_fetch(key, failing_fetcher)
    assert cache.get_or_fetch(key, succeeding_fetcher) == payload
```

- [ ] **Step 2: Run cache tests and confirm RED**

```bash
pytest -q tests/test_provider_cache.py
```

- [ ] **Step 3: Implement the small cache**

Use two dictionaries/sets only; no TTL/database/thread service:

```python
class CommandEntityCache:
    def __init__(self) -> None:
        self._payloads: dict[EntityCacheKey, Mapping[str, object]] = {}
        self._missing: set[EntityCacheKey] = set()

    def get_or_fetch(self, key, fetcher):
        if key in self._payloads:
            return self._payloads[key]
        if key in self._missing:
            return None
        payload = fetcher()  # exceptions escape and are not cached
        if payload is None:
            self._missing.add(key)
            return None
        self._payloads[key] = payload
        return payload
```

Validate/canonicalize non-empty provider/entity type/entity ID at `EntityCacheKey` construction.

- [ ] **Step 4: Extend provider specs for multi-scope semantic capability**

Keep existing names and registry shape. Add track/artist specs without overwriting release specs. Capability intent:

```python
MUSICBRAINZ_TRACK_SPEC = ProviderSpec(
    name="musicbrainz",
    display_name="MusicBrainz",
    supported_fields=frozenset({"genres", "moods", "lyrics_languages"}),
    scope=ProviderScope.TRACK,
)
MUSICBRAINZ_ARTIST_SPEC = ProviderSpec(
    name="musicbrainz",
    display_name="MusicBrainz",
    supported_fields=frozenset({"genres", "moods", "artist_countries", "artist_areas"}),
    scope=ProviderScope.ARTIST,
)
LASTFM_TRACK_SPEC = ProviderSpec(
    name="lastfm",
    display_name="Last.fm",
    supported_fields=frozenset({"genres", "styles", "moods"}),
    scope=ProviderScope.TRACK,
)
LASTFM_ARTIST_SPEC = ProviderSpec(... same semantic fields ..., scope=ProviderScope.ARTIST)
```

Release specs must advertise only actually implemented release semantic fields after this phase. `artist_languages` is derived by orchestration from Work languages, not fetched as an artist-profile field.

- [ ] **Step 5: Test registry collisions and lookups**

Assert these all coexist:

```python
("musicbrainz", ProviderScope.RELEASE)
("musicbrainz", ProviderScope.TRACK)
("musicbrainz", ProviderScope.ARTIST)
("lastfm", ProviderScope.RELEASE)
("lastfm", ProviderScope.TRACK)
("lastfm", ProviderScope.ARTIST)
```

Also run every existing provider-registry test to catch callers that still do `.get(name)` without scope.

- [ ] **Step 6: Run focused tests**

```bash
pytest -q tests/test_provider_cache.py tests/test_provider_specs.py
ruff check beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py
```

- [ ] **Step 7: Commit Task 2**

```bash
git add beetsplug/noqlenmeta/provider_cache.py beetsplug/noqlenmeta/providers/specs.py tests/test_provider_cache.py tests/test_provider_specs.py
git commit -m "refactor: add semantic provider cache scopes"
```

---

### Task 3: MusicBrainz exact semantic enrichment across Release, Recording, Work, Artist, and Area

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/musicbrainz.py`
- Create: `beetsplug/noqlenmeta/providers/musicbrainz_semantic.py`
- Modify: `beetsplug/noqlenmeta/genre_pipeline.py`
- Test: `tests/test_musicbrainz_provider.py`
- Create: `tests/test_musicbrainz_semantic.py`
- Extend: existing genre-pipeline/resolution tests

**Interfaces:**
- Consumes: `CommandEntityCache`, `SemanticEvidenceBundle`, `classify_semantic_tag`, existing `GenreEvidence`, exact MBIDs from Release/Track/Artist contexts.
- Produces:
  - `MusicBrainzSemanticClient` with cached `release`, `recording`, `work`, `artist`, and `area` exact lookups.
  - `MusicBrainzTrackProvider.get_semantic_evidence(context: TrackEnrichmentContext) -> SemanticEvidenceBundle`.
  - `MusicBrainzArtistProvider.get_semantic_evidence(context: ArtistEnrichmentContext) -> SemanticEvidenceBundle`.
  - release provider method `get_semantic_evidence(context: ReleaseEnrichmentContext) -> SemanticEvidenceBundle` while preserving existing `get_candidates()` behavior for ordinary release metadata.
  - pure helpers for Work language normalization and Area->country resolution.

- [ ] **Step 1: Add release semantic lookup tests**

Use sanitized representative payloads to assert a single release lookup can expose existing release metadata plus `genres`/`tags` when those capabilities are requested. Verify the includes passed to the fetch boundary are a union, not one request per field.

Example assertion:

```python
assert fetch_release.call_count == 1
assert set(fetch_release.call_args.kwargs["includes"]) >= {"labels", "media", "genres", "tags"}
```

Preserve existing release ID-response validation and ProviderError behavior.

- [ ] **Step 2: Add Recording -> Work language tests**

Cases:

```python
def test_recording_work_languages_are_canonical_and_deduplicated():
    # Recording has two Work relationships; Work payloads yield kor, eng, kor.
    ...
    assert bundle.metadata contains MetadataCandidate(
        field="lyrics_languages",
        value=("kor", "eng"),
        provider="musicbrainz",
        ...,
    )


def test_instrumental_or_missing_work_language_does_not_fabricate_language():
    ...
    assert no candidate has field == "lyrics_languages"
```

Also test multiple Works, malformed language values, and exact Work MBID deduplication through the command cache.

- [ ] **Step 3: Add Recording and Artist semantic-tag/genre tests**

Representative payload:

```python
{
    "id": RECORDING_MBID,
    "genres": [{"name": "k-pop", "count": 9}],
    "tags": [
        {"name": "dreamy", "count": 8},
        {"name": "seen live", "count": 2},
    ],
    "relations": [... Work ...],
}
```

Assert:
- `K-pop` becomes Track-scope `GenreEvidence`.
- `Dreamy` becomes Track-scope `MOOD` tag evidence.
- `seen live` never becomes a persisted metadata candidate.
- artist genres/tags are Artist-scope evidence and remain weaker by scope than eligible Track/Release evidence.

- [ ] **Step 4: Add Artist main-area/country tests**

Required cases:

```python
main area = Salvador (City), ancestry/ISO support resolves Brazil
-> artist_areas=("Salvador",)
-> artist_countries=("Brazil",)

main area = trustworthy city, country ancestry unavailable
-> artist_areas=("City",)
-> no artist_countries candidate

main area absent, begin-area trustworthy and structurally resolvable
-> controlled fallback may produce area/country

main area present + conflicting begin-area
-> main area wins; begin-area does not override
```

Never assert country from string parsing such as checking whether `"Salvador"` belongs to Brazil.

- [ ] **Step 5: Run MusicBrainz tests and confirm RED**

```bash
pytest -q tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py
```

- [ ] **Step 6: Implement `MusicBrainzSemanticClient` exact lookups**

Use the existing beets MusicBrainz boundary where it supports the required lookup. Keep fetch functions injectable for tests. Build includes once from enabled capabilities before the first exact lookup.

Cache keys:

```python
EntityCacheKey("musicbrainz", "release", release_mbid)
EntityCacheKey("musicbrainz", "recording", recording_mbid)
EntityCacheKey("musicbrainz", "work", work_mbid)
EntityCacheKey("musicbrainz", "artist", artist_mbid)
EntityCacheKey("musicbrainz", "area", area_mbid)
```

A response whose returned `id` does not canonicalize to the requested MBID is invalid and raises `ProviderError`; do not cache it as not-found.

- [ ] **Step 7: Normalize MusicBrainz genres/tags into structural evidence**

Direct MB `genres` -> `GenreEvidence(kind=GENRE, scope=<entity scope>)`.

MB community `tags` -> `classify_semantic_tag(...)`; if classified `GENRE`, convert to weaker `GenreEvidence(kind=COMMUNITY_TAG)`; otherwise retain `STYLE`/`MOOD` semantic evidence as appropriate. `ORIGIN` community tags remain classification evidence only and must not create `artist_countries`.

- [ ] **Step 8: Normalize Work languages and artist geography**

Language acceptance:

```python
def canonical_language_code(value: object) -> str | None:
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if re.fullmatch(r"[a-z]{3}", text) else None
```

Keep exact provider values that satisfy the canonical three-letter contract; do not translate names locally.

Geography must use structural Area data/type/ISO/parent relationships. Stop once a trustworthy country is established; if it cannot be, preserve specific main area without a country candidate.

- [ ] **Step 9: Wire MusicBrainz evidence into existing genre pipeline without changing genre policy**

Add Track/Release/Artist evidence to the evidence set passed to `resolve_genres`. Keep quality filtering before scope ranking and distinct-provider corroboration counting providers, not rows.

- [ ] **Step 10: Run focused semantic + genre regression tests**

```bash
pytest -q tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py
```

Expected: PASS; existing Genre Foundation tests unchanged unless fixture capabilities legitimately expand.

- [ ] **Step 11: Commit Task 3**

```bash
git add beetsplug/noqlenmeta/providers/musicbrainz.py beetsplug/noqlenmeta/providers/musicbrainz_semantic.py beetsplug/noqlenmeta/genre_pipeline.py tests/test_musicbrainz_provider.py tests/test_musicbrainz_semantic.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add MusicBrainz semantic evidence"
```

---

### Task 4: Last.fm lazy multi-scope fallback and Discogs structured-style authority

**Files:**
- Modify: `beetsplug/noqlenmeta/providers/lastfm.py`
- Modify: `beetsplug/noqlenmeta/providers/discogs.py` only if normalized structured output needs a small adapter change
- Modify: `beetsplug/noqlenmeta/semantic_resolution.py`
- Test: `tests/test_lastfm_provider.py`
- Test: existing Discogs provider tests
- Test: `tests/test_semantic_resolution.py`

**Interfaces:**
- Produces Last.fm semantic evidence for Track, Release, and Artist using exact context/known MBID when supported.
- Does not perform provider-wide fuzzy search.
- Structured Discogs `styles` remain primary style tuple; Discogs genre/style promotion behavior remains unchanged.
- Consumes `SemanticEvidenceBundle`, `classify_semantic_tag`, command cache, and Foundation provider contexts.

- [ ] **Step 1: Write Last.fm scope tests**

Add independent normalized adapter tests for:

```text
Track top tags -> TRACK SemanticTagEvidence
Album/release top tags -> RELEASE SemanticTagEvidence
Artist top tags -> ARTIST SemanticTagEvidence
```

Each test must retain native weight, source ID/URL, provider name, and scope. Tags classified as noise/unknown must not enter metadata.

- [ ] **Step 2: Write field-aware lazy fallback tests**

At orchestration boundary or a small pure helper, prove:

```python
# Track resolves both genre and mood -> no Release/Artist Last.fm call.
assert release_calls == 0
assert artist_calls == 0

# Track resolves genre but not mood -> Release may be queried for mood.
assert release_calls == 1

# Release resolves remaining mood -> Artist is not queried.
assert artist_calls == 0
```

The stop condition is per unresolved semantic field, not a single global boolean.

- [ ] **Step 3: Run Last.fm tests and confirm RED**

```bash
pytest -q tests/test_lastfm_provider.py tests/test_semantic_resolution.py
```

- [ ] **Step 4: Implement scoped Last.fm collection**

Reuse the existing authenticated request boundary and error semantics. Preserve current release genre behavior while routing returned tags through the Noqlen semantic classifier instead of treating arbitrary tags as genres.

When Last.fm accepts an MBID for the method being called, prefer the exact known MBID. Otherwise use the exact context fields (`artist`, `title`, `album_title`) already associated with the identified target. Do not add a separate search/disambiguation stage.

- [ ] **Step 5: Preserve Discogs structured style semantics**

Ensure the semantic resolver receives the structured Discogs `styles` candidate as structured evidence. Do not force those styles through the community style allowlist. Continue independent promotion into `GenreEvidence` only when `genres.promote_styles` is enabled and the genre taxonomy recognizes the style.

- [ ] **Step 6: Run provider and resolver tests**

```bash
pytest -q tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
ruff check beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/providers/discogs.py
```

- [ ] **Step 7: Commit Task 4**

```bash
git add beetsplug/noqlenmeta/providers/lastfm.py beetsplug/noqlenmeta/providers/discogs.py beetsplug/noqlenmeta/semantic_resolution.py tests/test_lastfm_provider.py tests/test_discogs_provider.py tests/test_semantic_resolution.py tests/test_genre_pipeline.py tests/test_genre_resolution.py
git commit -m "feat: add scoped semantic fallback"
```

---

### Task 5: Shared semantic orchestration, derived artist languages, and import/library parity

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_enrichment.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: existing importer enrichment module(s)
- Modify: `beetsplug/noqlenmeta/library_application.py` and/or `library_track_application.py` only where target application requires semantic fields
- Test: `tests/test_semantic_enrichment.py`
- Extend: `tests/test_v2_foundation_command.py`
- Extend: existing importer integration tests

**Interfaces:**
- Produces:
  - `SemanticFieldStatus(Enum)` values `RESOLVED`, `NO_EVIDENCE`, `UNAVAILABLE`, `CONFLICT`, `BLOCKED`.
  - `SemanticFieldOutcome(field: str, status: SemanticFieldStatus, value: MetadataValue | None, provenance: tuple[str, ...], reason: str)`.
  - `SemanticEnrichmentResult(metadata: tuple[MetadataCandidate, ...], genre_decision: ..., outcomes: tuple[SemanticFieldOutcome, ...])`.
  - `collect_semantic_enrichment(...)` as the single importer/library semantic orchestration entry point.
- Consumes release/track/artist contexts, enabled field set, provider registry/config, `CommandEntityCache`, semantic resolvers, and existing change-plan builders.

- [ ] **Step 1: Write pure orchestration tests for field gating**

Prove disabled fields do not trigger supporting lookups:

```python
fields = {"genres": True, "moods": False, "lyrics_languages": False}
result = collect_semantic_enrichment(...)
assert work_fetch_calls == 0
assert no outcome.field == "moods"
assert no outcome.field == "lyrics_languages"
```

Also prove `--write` is not part of the collection input and cannot increase provider call counts.

- [ ] **Step 2: Write `artist_languages` derivation tests**

Example:

```python
track_work_languages = (
    ("Artist A", 1, ("kor",)),
    ("Artist A", 1, ("kor", "eng")),
    ("Artist B", 2, ("jpn",)),
)
assert derive_artist_languages(track_work_languages) == ("kor", "eng", "jpn")
```

Add a test demonstrating that no extra artist-catalogue lookup is invoked to derive this field.

- [ ] **Step 3: Write multiple-credit area/country ordering tests**

For Artist A `South Korea`, Artist B `United States`, Artist C also `South Korea`, preserve first credit order and deduplicate final tuple:

```python
assert artist_countries == ("South Korea", "United States")
```

Do the same for areas.

- [ ] **Step 4: Write local-failure/outcome-state tests**

Required distinctions:

```text
Work exists but has no language -> NO_EVIDENCE
Work lookup network failure -> UNAVAILABLE
Two eligible moods with no deterministic winner -> CONFLICT
Lossless destination mapping unavailable -> BLOCKED
Resolved semantic field -> RESOLVED
```

A provider failure for one field/target must not erase unrelated successful candidates.

- [ ] **Step 5: Run orchestration tests and confirm RED**

```bash
pytest -q tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py
```

- [ ] **Step 6: Implement one shared semantic orchestration entry point**

Required collection sequence:

```text
1. Determine enabled semantic fields.
2. Build/obtain exact Release, Track, Artist contexts from already-known target IDs.
3. Create one CommandEntityCache for the command execution.
4. Collect MusicBrainz exact evidence for required scopes/entities.
5. Resolve fields that can already be resolved.
6. If Last.fm enabled, request Track -> Release -> Artist only for still-unresolved community semantic fields.
7. Combine Discogs structured styles/genres when Discogs is enabled.
8. Resolve genres/styles/moods.
9. Derive artist_languages from current-target Work languages.
10. Aggregate ordered/deduplicated artist areas/countries by credit order.
11. Emit candidates + explicit outcomes into existing ChangePlan construction.
```

Do not write DB/files inside this function.

- [ ] **Step 7: Route existing-library `beet nm` through the shared entry point**

Use Album targets plus their Items, and standalone Items where equivalent. Reuse stored MBIDs rather than searching. Preserve Foundation global preflight before mutation and existing partial-commit truthfulness.

- [ ] **Step 8: Route importer enrichment through the same entry point**

Use beets-selected exact release/recording/artist IDs already available in importer metadata. Do not re-identify the release. Import and library adapters may differ only in target extraction/application.

- [ ] **Step 9: Add parity scenarios**

For the same synthetic identified album/track fixtures, assert importer and library paths resolve identical canonical values for:

```text
genres
styles
moods
lyrics_languages
artist_languages
artist_countries
artist_areas
```

Allow only target-specific application representation differences explicitly required by beets.

- [ ] **Step 10: Run focused orchestration/parity tests**

```bash
pytest -q tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
ruff check beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/__init__.py
```

- [ ] **Step 11: Commit Task 5**

```bash
git add beetsplug/noqlenmeta/semantic_enrichment.py beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/library_application.py beetsplug/noqlenmeta/library_track_application.py tests/test_semantic_enrichment.py tests/test_v2_foundation_command.py tests/test_beets_integration.py
git add beetsplug/noqlenmeta tests
git commit -m "feat: integrate semantic enrichment pipeline"
```

Before committing, inspect `git diff --cached --name-only` and unstage unrelated files; the broad second `git add` is only to capture the exact existing importer module path if it differs from the names above.

---

### Task 6: Lossless semantic media fields and `--apply --write` observable verification

**Files:**
- Create: `beetsplug/noqlenmeta/semantic_media.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `beetsplug/noqlenmeta/file_sync.py`
- Test: create/extend the existing media-field/file-sync tests
- Extend: `tests/test_v2_foundation_command.py`

**Interfaces:**
- Produces `register_semantic_media_fields(plugin: BeetsPlugin) -> None` and file-sync mappings for semantic fields that have a lossless media representation.
- Consumes the existing Foundation `FileSyncPlan`/application safety model.

Official beets supports plugin-added `MediaField` descriptors through `BeetsPlugin.add_media_field()`. Use that extension point rather than bypassing MediaFile with ad-hoc direct Mutagen mutation.

- [ ] **Step 1: Write descriptor round-trip tests before registration**

Use temporary real media fixtures already used by Foundation. Cover at least FLAC/Vorbis-comment storage first because it naturally supports repeated/custom fields. Expected canonical tag keys:

```text
NOQLEN_STYLES
NOQLEN_MOODS
NOQLEN_LYRICS_LANGUAGES
NOQLEN_ARTIST_LANGUAGES
NOQLEN_ARTIST_COUNTRIES
NOQLEN_ARTIST_AREAS
```

The descriptor/codec must round-trip tuples exactly and preserve order. Tests must use values containing spaces/hyphens to prove no lossy split/join logic.

- [ ] **Step 2: Run media tests and confirm RED**

Run the exact new media test file plus current `file_sync` tests.

- [ ] **Step 3: Register MediaFile descriptors through the plugin**

Use `mediafile.MediaField`/storage styles behind `add_media_field`. For each supported container/tag family, use a representation that reads back as the same ordered tuple. If a format cannot represent the tuple losslessly with the chosen MediaFile abstraction, do not silently join it; leave that format/field unsupported so Foundation produces an explicit mapping blocker.

Keep canonical database names unchanged (`styles`, `moods`, `lyrics_languages`, `artist_languages`, `artist_countries`, `artist_areas`); tag storage names are an implementation detail documented as Noqlen custom tags.

- [ ] **Step 4: Extend `file_sync` mapping**

Add semantic canonical field -> registered MediaFile field mappings only after the descriptor is available. Keep blocker generation for unsupported fields/formats and keep global preflight before DB mutation when `--write` is requested.

- [ ] **Step 5: Verify the actual file after write**

Command integration test:

```python
invoke(plugin, library, ["--apply", "--write", "--all"])
fresh_file = MediaFile(path)
assert tuple(fresh_file.noqlen_moods) == ("Melancholic",)
assert tuple(fresh_file.noqlen_lyrics_languages) == ("kor", "eng")
```

Use the actual registered property names chosen in `semantic_media.py`; do not assert only internal `FileSyncResult` flags.

Also test that a deliberately unsupported lossless mapping blocks before DB mutation under the Foundation global-preflight contract.

- [ ] **Step 6: Run all file-sync/media tests**

```bash
pytest -q tests/test_v2_foundation_command.py tests/test_file_sync.py tests/test_media_snapshot.py
ruff check beetsplug/noqlenmeta/semantic_media.py beetsplug/noqlenmeta/file_sync.py
```

Include the exact semantic media test file created in Step 1 in the command.

- [ ] **Step 7: Commit Task 6**

```bash
git add beetsplug/noqlenmeta/semantic_media.py beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/file_sync.py tests
git commit -m "feat: sync semantic metadata to media files"
```

Inspect staged files before commit and exclude unrelated test changes.

---

### Task 7: Truthful preview/docs and integrated verification

**Files:**
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `README.md`
- Modify: `site-docs/reference/configuration.md`
- Modify: `site-docs/concepts/preview-apply-write.md`
- Modify: relevant provider/reference documentation already present in `site-docs/`
- Test: `tests/test_v2_foundation_command.py`
- Test: all semantic/provider/file-sync suites from Tasks 1-6

**Interfaces:**
- Normal CLI shows final semantic decisions + useful provenance and explicit `NO_EVIDENCE` / `UNAVAILABLE` / `CONFLICT` / `BLOCKED` status where relevant.
- Verbose/debug output may expose raw evidence; normal output does not dump every provider tag.

- [ ] **Step 1: Write preview/output regression tests**

Capture CLI output and assert useful lines rather than full snapshots:

```python
assert any("mood" in line and "Melancholic" in line for line in output)
assert any("MusicBrainz" in line for line in output)
assert any("lyrics_languages" in line and "kor" in line for line in output)
assert any("no-evidence" in line for line in missing_language_output)
assert any("unavailable" in line for line in provider_failure_output)
```

Verify normal output does not include rejected raw tags such as `seen live`.

- [ ] **Step 2: Run output tests and confirm RED where new reporting is absent**

```bash
pytest -q tests/test_v2_foundation_command.py
```

- [ ] **Step 3: Implement concise outcome/provenance rendering**

Normal preview should describe the resolved value, selected source/scope, and fallback note only when helpful. Keep raw evidence details behind existing verbosity/debug facilities.

Preserve Foundation separation of:

```text
database PREVIEW
file PREVIEW
application result
```

Do not print `stored`/`committed` before those observable actions have actually succeeded.

- [ ] **Step 4: Update configuration and behavior docs truthfully**

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

Document:
- MusicBrainz exact-ID semantic scope behavior;
- Discogs structured style authority;
- Last.fm lazy opt-in fallback;
- canonical three-letter language fields;
- contextual `artist_languages` semantics;
- geographic identification vs citizenship;
- Noqlen custom semantic media tags and any format limitations actually implemented;
- `--write` not causing provider work;
- Artwork/BPM still outside this phase.

- [ ] **Step 5: Run focused semantic suites**

```bash
pytest -q \
  tests/test_semantic_tags.py \
  tests/test_semantic_resolution.py \
  tests/test_provider_cache.py \
  tests/test_musicbrainz_provider.py \
  tests/test_musicbrainz_semantic.py \
  tests/test_lastfm_provider.py \
  tests/test_genre_pipeline.py \
  tests/test_genre_resolution.py \
  tests/test_semantic_enrichment.py \
  tests/test_v2_foundation_command.py
```

Include the exact semantic media/importer test modules created or extended in Tasks 5-6.

- [ ] **Step 6: Run full local verification**

```bash
ruff check .
pytest -q
python scripts/check_docs.py
python -m build
python -m twine check --strict dist/*
python scripts/check_distribution.py dist
```

Use the repository's exact current docs/check-distribution commands if their filenames have changed; do not omit an existing CI-equivalent check because a path changed.

- [ ] **Step 7: Run supported beets compatibility lanes**

Execute the repository's existing focused compatibility test command/environment for:

```text
beets == 2.12.0
latest beets < 3
```

Both must pass before PR readiness.

- [ ] **Step 8: Perform two observable smoke scenarios**

1. Existing-library dry run against deterministic fixtures/stubs: confirm semantic decisions appear with no DB/file mutation.
2. `--apply --write` against a synthetic temporary media fixture: reopen database and media file, verifying canonical persisted values rather than trusting internal result flags.

Never run tests against the user's real music library.

- [ ] **Step 9: Inspect final diff against the semantic branch base**

```bash
git status --short
git diff --stat a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
git diff --check a857b1cd5b88d39e2e1e7393b455645e1867c532..HEAD
```

Confirm no artwork/BPM/version-bump implementation leaked into the branch and no runtime dependency on beets LastGenre reappeared.

- [ ] **Step 10: Commit docs/reporting cleanup**

```bash
git add beetsplug/noqlenmeta/__init__.py README.md site-docs tests/test_v2_foundation_command.py
git commit -m "docs: document semantic enrichment behavior"
```

If Step 3 required no production change beyond an earlier task, commit only the docs/tests actually changed.

- [ ] **Step 11: PR readiness evidence**

Before opening/declaring the PR ready, record the exact current `HEAD`, full verification results, compatibility-lane results, and diff summary. PR base remains `docs/v2-enrichment-design`; do not retarget to `main` as part of this plan.

---

## Plan self-review checklist

The executor must preserve these coverage links:

- Spec §2 semantic classification -> Task 1.
- Spec §3 genres -> Tasks 1, 3, 4, 5.
- Spec §4 styles -> Tasks 1, 4, 5, 6.
- Spec §5 moods + `max_moods=1` -> Tasks 1, 3, 4, 5, 6.
- Spec §6 lyrics languages -> Tasks 3, 5, 6.
- Spec §7 contextual artist languages -> Task 5, 6.
- Spec §8 artist areas/countries -> Tasks 3, 5, 6.
- Spec §9 provider collection -> Tasks 2-5.
- Spec §10 cache/request efficiency -> Tasks 2-5.
- Spec §11 resolution/fallback -> Tasks 1, 4, 5.
- Spec §12 configuration -> Tasks 1, 2, 7.
- Spec §13 preview/outcomes -> Tasks 5, 7.
- Spec §14 failure behavior -> Tasks 2, 3, 4, 5, 6.
- Spec §15 import/library parity -> Task 5.
- Spec §16 verification -> Tasks 1-7, especially Task 7.
- Artwork/BPM non-goals -> Global Constraints + Task 7 final diff inspection.

No task authorizes merge or release. Merge remains a separate explicit user decision after fresh PR/CI/review verification.
