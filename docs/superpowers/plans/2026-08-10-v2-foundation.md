# Noqlen Meta v2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reusable v2 foundation for release, track, and artist enrichment: multi-scope provider capabilities, lossless multivalue persistence, generalized track/library planning, and explicit safe file synchronization behind `--write`.

**Architecture:** Keep the existing normalized-candidate -> resolver -> ChangePlan flow. Extend it with an Artist scope and target support rather than field-specific mini-systems. Release and track import paths continue using their existing adapters; existing-library Items gain the same track resolver/mapping semantics. File mutation is planned separately from database mutation and uses a verified candidate-copy/replace boundary; identity and AcoustID behavior remain unchanged.

**Tech Stack:** Python 3.10-3.14, beets >=2.12,<3, Confuse, MediaFile/Mutagen through beets, pytest, Ruff.

## Global Constraints

- Python support remains `>=3.10,<3.15`.
- Runtime dependency floor remains `beets>=2.12,<3`; Foundation adds no heavyweight audio dependency.
- The base plugin remains usable without another beets plugin.
- MusicBrainz identity and AcoustID evidence remain separate from ordinary enrichment.
- Existing `--identity`, `--identity-tags`, and `--acoustid` behavior must not regress.
- `--write` becomes ordinary-metadata file-write authority only together with `--apply`; the existing explicit `--identity-tags --write` workflow remains valid for backward compatibility.
- `--write` never enables providers, fields, fingerprinting, or local analysis. It applies only file changes already represented by the prepared ordinary metadata plan.
- Multivalued canonical metadata is never silently reduced to the first value.
- No real user music library is used in tests.
- No provider implementation is created only to satisfy a test or workflow pattern.
- The v2 target defaults are introduced only where the corresponding configuration can be truthful in this Foundation; Cover Art Archive activation and the `[audio]` dependency are deferred to the Artwork + Audio plan.

---

## File Structure

### Domain and capability registry

- Modify `beetsplug/noqlenmeta/domain.py` — add `ArtistEnrichmentContext`.
- Modify `beetsplug/noqlenmeta/providers/base.py` — add `ArtistMetadataProvider` protocol.
- Modify `beetsplug/noqlenmeta/providers/specs.py` — allow the same provider name to expose one capability per scope; add `ProviderScope.ARTIST`.
- Modify `beetsplug/noqlenmeta/providers/__init__.py` — export the artist protocol.
- Modify `tests/test_domain.py` and `tests/test_provider_specs.py`.

### Typed v2 fields and mapping

- Create `beetsplug/noqlenmeta/field_types.py` — one source of truth for plugin-declared typed flexible fields.
- Modify `beetsplug/noqlenmeta/__init__.py` — register item/album flexible-field types.
- Modify `beetsplug/noqlenmeta/beets_mapping.py` — map release `styles` losslessly to plural `styles` on selected `AlbumInfo`.
- Modify `beetsplug/noqlenmeta/library_mapping.py` — map persistent Album `styles` losslessly to plural `styles`.
- Modify `beetsplug/noqlenmeta/integration.py` — read plural styles first and legacy scalar `style` as fallback.
- Modify `beetsplug/noqlenmeta/library_integration.py` — same migration behavior for persistent Albums.
- Modify `beetsplug/noqlenmeta/beets_application.py` and `beetsplug/noqlenmeta/library_application.py` only as required to materialize `STRING_LIST` targets.
- Create `tests/test_field_types.py`; modify `tests/test_beets_mapping.py`, `tests/test_library_mapping.py`, and their application/integration tests.

### General track targets and existing-library parity

- Modify `beetsplug/noqlenmeta/track_mapping.py` — support string-list and numeric track targets.
- Modify `beetsplug/noqlenmeta/track_application.py` — materialize those target shapes into selected `TrackInfo`.
- Modify `beetsplug/noqlenmeta/track_integration.py` — read all canonical v2 track fields from selected/imported and library Item data.
- Modify `beetsplug/noqlenmeta/track_planning.py` — expose one generic track resolver builder reused by importer and library adapters.
- Create `beetsplug/noqlenmeta/library_track_application.py` — stale-safe Item database application using the shared `TrackTargetPlan`.
- Create `beetsplug/noqlenmeta/library_track_preview.py` — existing-library Item preview only; no provider logic.
- Modify `tests/test_track_mapping.py`, `tests/test_track_application.py`, and create `tests/test_library_track_application.py`.

### Safe generic file synchronization

- Create `beetsplug/noqlenmeta/media_snapshot.py` — generic read-only media/file snapshot and safe-copy primitives.
- Modify `beetsplug/noqlenmeta/identity/tag_filesystem.py` — consume/re-export the extracted generic primitives while retaining identity-specific logical snapshots.
- Create `beetsplug/noqlenmeta/file_sync.py` — generic ordinary-metadata `FileSyncPlan`, mapping, preflight, candidate-write, verification, replace, and result.
- Create `tests/test_media_snapshot.py` and `tests/test_file_sync.py`.
- Re-run the complete identity-tag suite after the extraction.

### CLI/config integration

- Modify `beetsplug/noqlenmeta/configuration.py` — add v2 field keys and `local_analysis` structure; enable safe zero-credential MusicBrainz by default.
- Modify `beetsplug/noqlenmeta/resolver.py` — plural `moods` and v2 canonical field rules, without pretending unavailable providers exist.
- Modify `beetsplug/noqlenmeta/__init__.py` — generalize `--write`, collect ordinary release + Item plans before mutation, and reuse one track-candidate collection path for import/library.
- Modify `site-docs/reference/fields.md`, `site-docs/reference/configuration.md`, `site-docs/reference/commands.md`, and `site-docs/examples/full-config.yaml` for Foundation-visible contracts.
- Add focused CLI tests in the existing command test module if one exists; otherwise create `tests/test_v2_foundation_command.py`.

---

### Task 1: Add Artist scope and make provider capabilities multi-scope-safe

**Files:**
- Modify: `beetsplug/noqlenmeta/domain.py`
- Modify: `beetsplug/noqlenmeta/providers/base.py`
- Modify: `beetsplug/noqlenmeta/providers/specs.py`
- Modify: `beetsplug/noqlenmeta/providers/__init__.py`
- Modify: `beetsplug/noqlenmeta/resolver.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Test: `tests/test_domain.py`
- Test: `tests/test_provider_specs.py`

**Interfaces:**
- Produces: `ArtistEnrichmentContext(name: str, sort_name: str | None = None, credit_name: str | None = None, credit_index: int | None = None, external_ids: tuple[ExternalIdentifier, ...] = ())`.
- Produces: `ArtistMetadataProvider.get_candidates(context: ArtistEnrichmentContext) -> Sequence[MetadataCandidate]`.
- Produces: `ProviderScope.ARTIST`.
- Produces: `BUILTIN_PROVIDER_SPECS: Mapping[tuple[str, ProviderScope], ProviderSpec]` and `BUILTIN_PROVIDER_NAMES: frozenset[str]` so later MusicBrainz release/track/artist specs may coexist.
- Preserves: `BUILTIN_RELEASE_PROVIDER_SPECS` and `BUILTIN_TRACK_PROVIDER_SPECS`; adds `BUILTIN_ARTIST_PROVIDER_SPECS`.

- [ ] **Step 1: Write failing Artist context tests**

Add tests equivalent to:

```python
from beetsplug.noqlenmeta.domain import ArtistEnrichmentContext, ExternalIdentifier


def test_artist_context_preserves_credit_identity() -> None:
    mbid = ExternalIdentifier("musicbrainz.artist", "00000000-0000-0000-0000-000000000001")
    context = ArtistEnrichmentContext(
        "Synthetic Artist",
        sort_name="Artist, Synthetic",
        credit_name="Synthetic Artist feat.",
        credit_index=2,
        external_ids=(mbid,),
    )
    assert context.name == "Synthetic Artist"
    assert context.credit_index == 2
    assert context.external_ids == (mbid,)


def test_artist_context_rejects_non_positive_credit_index() -> None:
    with pytest.raises(ValueError, match="credit index"):
        ArtistEnrichmentContext("Synthetic Artist", credit_index=0)
```

- [ ] **Step 2: Run the Artist tests and verify failure**

Run:

```bash
pytest tests/test_domain.py -q
```

Expected: FAIL because `ArtistEnrichmentContext` does not exist.

- [ ] **Step 3: Implement `ArtistEnrichmentContext` with the same immutable validation discipline as Release/Track contexts**

Add:

```python
@dataclass(frozen=True, slots=True)
class ArtistEnrichmentContext:
    name: str
    sort_name: str | None = None
    credit_name: str | None = None
    credit_index: int | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "artist name"))
        object.__setattr__(self, "sort_name", _optional_text(self.sort_name, "artist sort name"))
        object.__setattr__(self, "credit_name", _optional_text(self.credit_name, "artist credit name"))
        if self.credit_index is not None and (
            isinstance(self.credit_index, bool)
            or not isinstance(self.credit_index, int)
            or self.credit_index <= 0
        ):
            raise ValueError("credit index must be a positive integer")
        ids = tuple(self.external_ids)
        if not all(isinstance(value, ExternalIdentifier) for value in ids):
            raise TypeError("external_ids must contain ExternalIdentifier values")
        object.__setattr__(self, "external_ids", ids)
```

- [ ] **Step 4: Write failing provider-registry tests for duplicate provider names across scopes**

Update `tests/test_provider_specs.py` to assert:

```python
artist_spec = ProviderSpec(
    "musicbrainz", "MusicBrainz", frozenset({"artist_countries"}), ProviderScope.ARTIST
)
assert (MUSICBRAINZ_SPEC.name, ProviderScope.RELEASE) in BUILTIN_PROVIDER_SPECS
assert "musicbrainz" in BUILTIN_PROVIDER_NAMES
assert ProviderScope.ARTIST.value == "artist"
```

Also construct a local test registry with release + artist specs sharing `name="musicbrainz"` and verify keying by `(name, scope)` does not collide.

- [ ] **Step 5: Refactor provider capability registries and add Artist protocol**

Use the following registry shape:

```python
ProviderKey: TypeAlias = tuple[str, ProviderScope]
BUILTIN_PROVIDER_SPECS: Mapping[ProviderKey, ProviderSpec] = MappingProxyType(
    {(spec.name, spec.scope): spec for spec in _BUILTIN_PROVIDER_CAPABILITIES}
)
BUILTIN_PROVIDER_NAMES = frozenset(spec.name for spec in _BUILTIN_PROVIDER_CAPABILITIES)
```

Build the three scope-specific mappings from `_BUILTIN_PROVIDER_CAPABILITIES`. Change resolver/plugin loops that need configuration provider names to iterate `BUILTIN_PROVIDER_NAMES`, not `BUILTIN_PROVIDER_SPECS` keys.

Add to `providers/base.py`:

```python
@runtime_checkable
class ArtistMetadataProvider(Protocol):
    name: str
    supported_fields: frozenset[str]

    def get_candidates(
        self, context: ArtistEnrichmentContext
    ) -> Sequence[MetadataCandidate]: ...
```

- [ ] **Step 6: Run focused tests**

```bash
pytest tests/test_domain.py tests/test_provider_specs.py tests/test_resolver.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add beetsplug/noqlenmeta/domain.py beetsplug/noqlenmeta/providers/base.py beetsplug/noqlenmeta/providers/specs.py beetsplug/noqlenmeta/providers/__init__.py beetsplug/noqlenmeta/resolver.py beetsplug/noqlenmeta/__init__.py tests/test_domain.py tests/test_provider_specs.py
git commit -m "refactor: add v2 enrichment scopes"
```

---

### Task 2: Add typed v2 fields and make `styles` losslessly plural

**Files:**
- Create: `beetsplug/noqlenmeta/field_types.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `beetsplug/noqlenmeta/beets_mapping.py`
- Modify: `beetsplug/noqlenmeta/library_mapping.py`
- Modify: `beetsplug/noqlenmeta/integration.py`
- Modify: `beetsplug/noqlenmeta/library_integration.py`
- Modify: `beetsplug/noqlenmeta/beets_application.py`
- Modify: `beetsplug/noqlenmeta/library_application.py`
- Create: `tests/test_field_types.py`
- Modify: `tests/test_beets_mapping.py`
- Modify: `tests/test_library_mapping.py`

**Interfaces:**
- Produces: `ITEM_FIELD_TYPES` for `moods`, `lyrics_languages`, `artist_countries`, `artist_areas`, `artist_languages` using `types.MULTI_VALUE_DSV`.
- Produces: `ALBUM_FIELD_TYPES` for `styles`, `artist_countries`, `artist_areas`, `artist_languages` using `types.MULTI_VALUE_DSV`.
- Does not redeclare built-in `Item.bpm`.
- Changes release target: canonical `styles` -> `styles` with `STRING_LIST` shape.
- Migration read order: plural flexible `styles` first; fixed legacy `style` only when plural is absent/empty.

- [ ] **Step 1: Write typed-field and round-trip failing tests**

Create `tests/test_field_types.py` with assertions such as:

```python
from beets.dbcore import types
from beets.library import Album, Item, Library
from beetsplug.noqlenmeta import NoqlenMetaPlugin


def test_plugin_declares_v2_multivalue_types() -> None:
    plugin = NoqlenMetaPlugin()
    assert plugin.album_types["styles"] is types.MULTI_VALUE_DSV
    assert plugin.item_types["moods"] is types.MULTI_VALUE_DSV
    assert "bpm" not in plugin.item_types


def test_styles_round_trip_as_multiple_album_values(tmp_path) -> None:
    plugin = NoqlenMetaPlugin()
    lib = Library(str(tmp_path / "library.db"))
    album = Album(album="Synthetic", albumartist="Artist")
    album["styles"] = ["Progressive Metal", "Technical Death Metal"]
    album.add(lib)
    fresh = lib.get_album(album.id)
    assert fresh is not None
    assert fresh["styles"] == ["Progressive Metal", "Technical Death Metal"]
```

Use the repository's existing plugin-isolation fixture if needed so global beets plugin type registration does not leak across tests.

- [ ] **Step 2: Run tests and verify they fail**

```bash
pytest tests/test_field_types.py tests/test_beets_mapping.py tests/test_library_mapping.py -q
```

Expected: FAIL because typed v2 fields and plural style targets are absent.

- [ ] **Step 3: Add the field type registry**

Create:

```python
from types import MappingProxyType
from beets.dbcore import types

ITEM_FIELD_TYPES = MappingProxyType({
    "moods": types.MULTI_VALUE_DSV,
    "lyrics_languages": types.MULTI_VALUE_DSV,
    "artist_countries": types.MULTI_VALUE_DSV,
    "artist_areas": types.MULTI_VALUE_DSV,
    "artist_languages": types.MULTI_VALUE_DSV,
})

ALBUM_FIELD_TYPES = MappingProxyType({
    "styles": types.MULTI_VALUE_DSV,
    "artist_countries": types.MULTI_VALUE_DSV,
    "artist_areas": types.MULTI_VALUE_DSV,
    "artist_languages": types.MULTI_VALUE_DSV,
})
```

Register on `NoqlenMetaPlugin` with fresh dictionaries so callers cannot mutate the module constants:

```python
item_types = dict(ITEM_FIELD_TYPES)

@property
def album_types(self):
    return dict(ALBUM_FIELD_TYPES)
```

- [ ] **Step 4: Change import and library release mappings for plural `styles`**

In both target registries use:

```python
BeetsFieldTarget("styles", "styles", BeetsTargetShape.STRING_LIST)
LibraryFieldTarget("styles", "styles", BeetsTargetShape.STRING_LIST)
```

Remove the special behavior that converted one style to `style` and blocked two styles. `STRING_LIST` continues carrying the immutable tuple in the plan and materializes a list only at the application boundary.

- [ ] **Step 5: Add legacy scalar style fallback without overwriting plural values**

Implement the same precedence in import and persistent library readers:

```python
styles = _text_tuple(source.get("styles"))
if not styles:
    legacy_style = _optional_text(source.style)
    if legacy_style is not None:
        styles = (legacy_style,)
if styles:
    current_values["styles"] = styles
```

For `AlbumInfo`, use its arbitrary-attribute mapping (`album_info.get("styles")`). For persistent Album, use `album.get("styles", None)`.

- [ ] **Step 6: Add explicit migration tests**

Cover all three cases:

```python
assert current_values_from_library_album(Album(style="Legacy"))["styles"] == ("Legacy",)

album = Album(style="Legacy")
album["styles"] = ["Modern A", "Modern B"]
assert current_values_from_library_album(album)["styles"] == ("Modern A", "Modern B")

info = AlbumInfo([], artist="Artist", album="Album", style="Legacy")
info["styles"] = ["Modern A", "Modern B"]
assert current_values_from_album_info(info)["styles"] == ("Modern A", "Modern B")
```

- [ ] **Step 7: Run focused mapping/application tests**

```bash
pytest tests/test_field_types.py tests/test_beets_mapping.py tests/test_library_mapping.py tests/test_beets_application.py tests/test_library_application.py -q
```

Expected: PASS; multi-style tests assert no mapping blocker and preserve both values.

- [ ] **Step 8: Commit**

```bash
git add beetsplug/noqlenmeta/field_types.py beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/beets_mapping.py beetsplug/noqlenmeta/library_mapping.py beetsplug/noqlenmeta/integration.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/beets_application.py beetsplug/noqlenmeta/library_application.py tests/test_field_types.py tests/test_beets_mapping.py tests/test_library_mapping.py tests/test_beets_application.py tests/test_library_application.py
git commit -m "feat: add lossless v2 field storage"
```

---

### Task 3: Generalize track enrichment targets and add existing-library Item application

**Files:**
- Modify: `beetsplug/noqlenmeta/track_mapping.py`
- Modify: `beetsplug/noqlenmeta/track_application.py`
- Modify: `beetsplug/noqlenmeta/track_integration.py`
- Modify: `beetsplug/noqlenmeta/track_planning.py`
- Create: `beetsplug/noqlenmeta/library_track_application.py`
- Create: `beetsplug/noqlenmeta/library_track_preview.py`
- Modify: `tests/test_track_mapping.py`
- Modify: `tests/test_track_application.py`
- Create: `tests/test_library_track_application.py`

**Interfaces:**
- Extends `TrackTargetShape` with `STRING_LIST` and `SCALAR_FLOAT`.
- Target registry:
  - `lyrics -> lyrics / SCALAR_STRING`
  - `bpm -> bpm / SCALAR_FLOAT`
  - `moods -> moods / STRING_LIST`
  - `lyrics_languages -> lyrics_languages / STRING_LIST`
  - `artist_countries -> artist_countries / STRING_LIST`
  - `artist_areas -> artist_areas / STRING_LIST`
  - `artist_languages -> artist_languages / STRING_LIST`
- Keeps `synced_lyrics` as an explicit mapping blocker.
- Produces: `build_track_planning_result(context, current_values, *, candidates, policy) -> TrackPlanningResult`.
- Keeps `build_import_track_planning_result(...)` as an importer adapter around the generic builder.
- Produces: `apply_library_track_plan(item: Item, plan: TrackTargetPlan, mode: TrackApplicationMode = STRICT) -> LibraryTrackApplicationResult`.

- [ ] **Step 1: Write failing shape/mapping tests**

Add:

```python
@pytest.mark.parametrize(
    ("field", "value", "target", "shape"),
    [
        ("bpm", 126.4, "bpm", TrackTargetShape.SCALAR_FLOAT),
        ("moods", ("Dark", "Energetic"), "moods", TrackTargetShape.STRING_LIST),
        ("lyrics_languages", ("English", "Korean"), "lyrics_languages", TrackTargetShape.STRING_LIST),
    ],
)
def test_v2_track_targets_are_lossless(field, value, target, shape):
    result = map_change_plan_to_track_info(ChangePlan(changes=(planned_change(field, value),)))
    mapped = result.mapped_changes[0]
    assert mapped.target_field == target
    assert mapped.target_shape is shape
    assert mapped.target_value == value
```

- [ ] **Step 2: Run track mapping tests and verify failure**

```bash
pytest tests/test_track_mapping.py -q
```

Expected: FAIL on unsupported v2 fields/shapes.

- [ ] **Step 3: Implement track target shapes and strict value validation**

Rules:

```python
if target.shape is TrackTargetShape.STRING_LIST:
    require a non-empty tuple of canonical non-empty strings
elif target.shape is TrackTargetShape.SCALAR_FLOAT:
    require int|float, reject bool/non-finite, materialize float(value)
elif target.shape is TrackTargetShape.SCALAR_STRING:
    require a non-empty canonical string
```

Do not coerce a tuple into a joined string.

- [ ] **Step 4: Expand current-value readers and generic track planning**

`track_integration._current_track_values` must read:

```python
TEXT_FIELDS = ("lyrics",)
MULTI_FIELDS = (
    "moods",
    "lyrics_languages",
    "artist_countries",
    "artist_areas",
    "artist_languages",
)
```

Read `bpm` as a finite positive number and canonicalize to `float`. Continue reading `synced_lyrics` only for its existing semantics.

Refactor `track_planning.py` so the shared core is:

```python
@dataclass(frozen=True, slots=True)
class TrackPlanningResult:
    context: TrackEnrichmentContext
    candidate_count: int
    decisions: tuple[FieldDecision, ...]
    change_plan: ChangePlan
    target_plan: TrackTargetPlan


def build_track_planning_result(
    context: TrackEnrichmentContext,
    current_values: Mapping[str, MetadataValue],
    *,
    candidates: Sequence[MetadataCandidate],
    policy: ResolutionPolicy,
) -> TrackPlanningResult:
    decisions = resolve_metadata(current_values, tuple(candidates), policy)
    change_plan = build_change_plan(decisions)
    return TrackPlanningResult(
        context,
        len(tuple(candidates)),
        decisions,
        change_plan,
        map_change_plan_to_track_info(change_plan),
    )
```

Collect candidates once before counting so generators cannot be consumed twice.

- [ ] **Step 5: Adapt importer planning without changing its public behavior**

`build_import_track_planning_result` computes `effective_current_values_for_import_track(...)`, calls the generic builder, and returns the existing import-specific bundle. Existing LRCLIB tests must remain unchanged apart from type additions.

- [ ] **Step 6: Write failing existing-library Item application tests**

Create tests that use a temporary `Library` and real persisted Item:

```python
plan = map_change_plan_to_track_info(
    ChangePlan(changes=(planned_change("moods", ("Dark", "Energetic")),))
)
result = apply_library_track_plan(item, plan)
fresh = lib.get_item(item.id)
assert fresh is not None
assert fresh["moods"] == ["Dark", "Energetic"]
assert result.stored
```

Also test stale DB state, pre-existing dirty state, strict blocker, partial mode, forged plan, and `bpm=126.4` round trip.

- [ ] **Step 7: Implement stale-safe library Item application**

The contract mirrors persistent Album application but uses Item-local reads only:

```python
fresh = item.get_fresh_from_db()
current_values = current_values_from_library_item(fresh)
for change in plan.mapped_changes:
    if current_values.get(change.canonical_field) != change.source.before:
        raise LibraryTrackApplicationError(...)
for target_field, value in materialized:
    item[target_field] = value
item.store()
```

Require exact type equality for stale checks, validate canonical remapping, reject dirty Items, and materialize list/float/string according to `TrackTargetShape`.

- [ ] **Step 8: Add a concise library Item preview**

Render Item identity, database target, planned values, blockers, and application state. Do not include paths or file contents in this preview; file effects belong to Task 5.

- [ ] **Step 9: Run focused track tests**

```bash
pytest tests/test_track_mapping.py tests/test_track_application.py tests/test_track_planning.py tests/test_library_track_application.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add beetsplug/noqlenmeta/track_mapping.py beetsplug/noqlenmeta/track_application.py beetsplug/noqlenmeta/track_integration.py beetsplug/noqlenmeta/track_planning.py beetsplug/noqlenmeta/library_track_application.py beetsplug/noqlenmeta/library_track_preview.py tests/test_track_mapping.py tests/test_track_application.py tests/test_track_planning.py tests/test_library_track_application.py
git commit -m "feat: generalize v2 track enrichment"
```

---

### Task 4: Extract generic media snapshot/copy primitives without weakening identity-tag safety

**Files:**
- Create: `beetsplug/noqlenmeta/media_snapshot.py`
- Modify: `beetsplug/noqlenmeta/identity/tag_filesystem.py`
- Modify: `beetsplug/noqlenmeta/identity/tag_application.py` only for import path/name changes if required
- Create: `tests/test_media_snapshot.py`
- Run: all existing `tests/test_identity_tag_*.py` / identity tag tests present in the repository

**Interfaces:**
- Produces immutable `FilesystemMetadata`, `MediaFileFingerprint`, and `MediaFileSnapshot` values independent of MusicBrainz fields.
- Produces `snapshot_media_file(path: bytes, *, fields: Iterable[str]) -> MediaFileSnapshot`.
- Produces `copy_regular_file_without_source_atime(...)`, `filesystem_metadata(path)`, `verify_candidate_metadata(...)`, and `freeze_media_value(...)` in the generic module.
- Identity-specific snapshot code continues to expose the same public names/results to existing callers.

- [ ] **Step 1: Write generic snapshot tests before moving code**

Test a temporary tagged fixture and require:

```python
snapshot = snapshot_media_file(path, fields=("title", "artist"))
assert snapshot.path == path
assert dict(snapshot.values)["title"] == "Synthetic Title"
assert snapshot.filesystem_metadata.size == os.stat(path).st_size
```

Also test rejection of symlinks/non-regular files and deterministic freezing of tuple/list-like MediaFile values.

- [ ] **Step 2: Run the new tests and verify failure**

```bash
pytest tests/test_media_snapshot.py -q
```

Expected: FAIL because `media_snapshot.py` does not exist.

- [ ] **Step 3: Move only generic filesystem/media primitives**

The new module owns generic types/functions; `identity/tag_filesystem.py` imports them and keeps only identity-specific structures such as the partition between identity values and unrelated values.

Do not alter the identity-tag candidate/backup/replace algorithm in this task. This task is an extraction, not a rewrite.

- [ ] **Step 4: Preserve identity compatibility names where tests/imports rely on them**

If `IdentityTagFilesystemMetadata` or `IdentityTagFileFingerprint` are imported outside `tag_filesystem.py`, use aliases rather than editing unrelated callers:

```python
IdentityTagFilesystemMetadata = FilesystemMetadata
IdentityTagFileFingerprint = MediaFileFingerprint
```

- [ ] **Step 5: Run generic + complete identity-tag regression tests**

```bash
pytest tests/test_media_snapshot.py tests -q -k 'identity_tag'
```

Expected: PASS with no identity behavior change.

- [ ] **Step 6: Commit**

```bash
git add beetsplug/noqlenmeta/media_snapshot.py beetsplug/noqlenmeta/identity/tag_filesystem.py beetsplug/noqlenmeta/identity/tag_application.py tests/test_media_snapshot.py
git commit -m "refactor: extract safe media snapshot primitives"
```

---

### Task 5: Add generic ordinary-metadata file sync and generalize `--write`

**Files:**
- Create: `beetsplug/noqlenmeta/file_sync.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `beetsplug/noqlenmeta/library_integration.py`
- Modify: `beetsplug/noqlenmeta/library_track_preview.py`
- Create: `tests/test_file_sync.py`
- Create or modify: `tests/test_v2_foundation_command.py` / existing command tests

**Interfaces:**
- Produces: `FileTagTarget(canonical_field, media_field, shape)`.
- Produces: `FileTagChange(canonical_field, media_field, before, after, source)`.
- Produces: `FileSyncPlan(item_id, path, snapshot, changes=(), blockers=())`.
- Produces: `plan_file_sync(item: Item, changes: Sequence[PlannedChange]) -> FileSyncPlan`.
- Produces: `verify_file_sync_plan(lib: Library, plan: FileSyncPlan) -> None`.
- Produces: `apply_file_sync_plan(lib: Library, plan: FileSyncPlan) -> FileSyncResult`.
- Foundation-supported built-in media mappings: `genres -> genres`, `labels -> label`, `country -> country`, `year -> year`, `lyrics -> lyrics`, `bpm -> bpm`. Other canonical fields are blockers until their MediaFile descriptors are deliberately added in later plans.

- [ ] **Step 1: Write pure planner tests**

Examples:

```python
plan = plan_file_sync(item, (planned_change("bpm", 126.4),))
assert plan.blockers == ()
assert plan.changes[0].media_field == "bpm"
assert plan.changes[0].after == 126.4

blocked = plan_file_sync(item, (planned_change("moods", ("Dark",)),))
assert blocked.changes == ()
assert blocked.blockers[0].canonical_field == "moods"
```

Assert planner rejects paths that are absent/non-regular and never mutates the Item.

- [ ] **Step 2: Run planner tests and verify failure**

```bash
pytest tests/test_file_sync.py -q
```

Expected: FAIL because file sync does not exist.

- [ ] **Step 3: Implement canonical file mapping and snapshot planning**

Use an immutable mapping and validate that every declared media target is present in `MediaFile.fields()` at runtime. A canonical value that cannot be represented by that MediaFile field becomes a blocker; it is never string-joined.

- [ ] **Step 4: Write application tests using temporary synthetic media files**

Cover:

1. `bpm` write changes only BPM.
2. `lyrics` write changes only lyrics.
3. unrelated title/artist tags remain byte-logically equivalent after candidate save.
4. source changed after planning -> preflight abort before replace.
5. forged plan -> rejected.
6. candidate save failure -> original file remains.
7. replace succeeds but final DB mtime/finalization fails -> result/error truthfully reports committed/uncertain state and retains recovery material when required.

Read the resulting file with `MediaFile` after success; do not accept only an internal success flag.

- [ ] **Step 5: Implement verified candidate-copy application**

The application order is fixed:

```text
validate canonical plan
→ verify fresh Item + source snapshot
→ create same-directory candidate
→ copy source without mutating source
→ apply only planned MediaFile fields to candidate
→ save candidate
→ verify planned fields changed and unrelated snapshot fields did not
→ fsync candidate
→ verify source still matches original snapshot
→ create verified backup/recovery artifact
→ os.replace(candidate, source)
→ fsync directory
→ verify replaced file outcome
→ update operational Item mtime in DB
→ emit normal beets write/database notifications
→ remove recovery artifact
```

Use the same error-state vocabulary as the identity writer (`committed`, `state_uncertain`, `recovery_artifact_retained`) so callers can report partial outcomes consistently.

- [ ] **Step 6: Change CLI validation for ordinary `--write` without breaking identity-tags**

Replace the old global rule:

```python
if write_enabled and not identity_tags_enabled:
    raise ui.UserError("noqlenmeta: --write requires --identity-tags")
```

with:

```python
if write_enabled and not identity_tags_enabled and not apply_enabled:
    raise ui.UserError("noqlenmeta: --write requires --apply for ordinary metadata")
```

Keep:

```text
--identity-tags --write       allowed (legacy explicit file-sync workflow)
--identity-tags --apply       rejected
ordinary --write without --apply rejected
--acoustid --write            rejected
```

- [ ] **Step 7: Make ordinary command prepare all file plans before any file mutation**

For selected release plans, fan supported release changes out to `album.items()`; for selected library Item track plans, use the Item itself. Deduplicate by `(item.id, media_field)` and reject conflicting planned values rather than letting last-write win.

Required command order under `--apply --write`:

```text
collect provider evidence
→ resolve and prepare every DB target plan
→ prepare every FileSyncPlan
→ render DB + file previews
→ preflight every writable FileSyncPlan
→ apply database plans
→ apply file plans
→ report committed/blocked/partial results
```

No file is written before every file plan has passed command-wide preflight.

- [ ] **Step 8: Add CLI authority tests**

At minimum:

```python
with pytest.raises(ui.UserError, match="--write requires --apply"):
    run_nm(write=True, apply=False)

run_nm(identity_tags=True, write=True)  # remains valid
run_nm(apply=True, write=True)          # ordinary path accepted
```

Add a synthetic end-to-end ordinary library command test that changes a writable field, reads the DB result, then reads the media file result.

- [ ] **Step 9: Run focused file/CLI/identity tests**

```bash
pytest tests/test_file_sync.py tests -q -k 'identity_tag or v2_foundation_command or file_sync'
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add beetsplug/noqlenmeta/file_sync.py beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/library_integration.py beetsplug/noqlenmeta/library_track_preview.py tests/test_file_sync.py tests/test_v2_foundation_command.py
git commit -m "feat: add safe ordinary file synchronization"
```

---

### Task 6: Wire Foundation configuration, existing-library track parity, docs, and full verification

**Files:**
- Modify: `beetsplug/noqlenmeta/configuration.py`
- Modify: `beetsplug/noqlenmeta/resolver.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `site-docs/reference/fields.md`
- Modify: `site-docs/reference/configuration.md`
- Modify: `site-docs/reference/commands.md`
- Modify: `site-docs/examples/full-config.yaml`
- Modify/create focused configuration/command tests.

**Interfaces:**
- Foundation field defaults:
  - existing `genres`, `styles`, release fields remain enabled as currently appropriate;
  - `moods: true`, `bpm: true`, `lyrics_languages: true`, `artist_countries: true`, `artist_areas: false`, `artist_languages: true`, `cover: true`;
  - retain `lyrics` and `synced_lyrics` existing explicit settings.
- Remove singular `mood` config/rule in favor of canonical `moods`.
- `providers.musicbrainz.enabled` becomes `true` as the approved safe zero-credential default.
- Add `local_analysis.bpm.enabled: true`, `local_analysis.bpm.mode: fallback`, `local_analysis.mood.enabled: false`; Foundation stores/validates this structure but does not run an audio backend.
- Cover Art Archive provider config is introduced in the Artwork + Audio plan together with its real adapter; do not add an enabled provider entry that has no implementation.
- Existing-library ordinary command evaluates both release and track scopes against the same query: `lib.albums(query)` for release plans and `lib.items(query)` for track plans. `--all` selects both sets. Scope execution is skipped independently when no enabled source can contribute.

- [ ] **Step 1: Write configuration-default tests**

Assert exact canonical keys and that the deprecated singular `mood` key is absent:

```python
config = default_config()
assert config["fields"]["moods"] is True
assert "mood" not in config["fields"]
assert config["fields"]["artist_areas"] is False
assert config["providers"]["musicbrainz"]["enabled"] is True
assert config["local_analysis"] == {
    "bpm": {"enabled": True, "mode": "fallback"},
    "mood": {"enabled": False},
}
```

- [ ] **Step 2: Update resolver field rules without claiming unavailable capability**

Use canonical authorities that refer only to recognized provider names:

```python
"moods": ("lastfm", "musicbrainz"),
"lyrics_languages": ("musicbrainz",),
"artist_countries": ("musicbrainz",),
"artist_areas": ("musicbrainz",),
"artist_languages": ("musicbrainz",),
```

Do not add `local` to resolver provider validation until the Artwork + Audio implementation adds the analyzer evidence source. `bpm` may have an empty/no eligible authority in Foundation; the field can be enabled without inventing evidence.

- [ ] **Step 3: Refactor track candidate collection for import + library reuse**

Extract:

```python
def _collect_track_candidates(
    self,
    context: TrackEnrichmentContext,
    policy: ResolutionPolicy,
) -> tuple[MetadataCandidate, ...]:
    candidates: list[MetadataCandidate] = []
    if provider_can_contribute(policy, LRCLIB_SPEC):
        candidates.extend(self._collect_provider_candidates(
            LRCLIB_SPEC,
            lambda: self._lrclib_candidates(context),
        ))
    return tuple(candidates)
```

Importer and existing-library track paths both call this function. This makes current LRCLIB enrichment available to selected existing-library Items under the same resolver rules rather than creating a second provider path.

- [ ] **Step 4: Make the ordinary library command process both scopes coherently**

Prepare release and Item plans first. Do not duplicate Item work when an Item appears through both release fan-out and direct track selection: release changes and track changes may both target one file, but database plans remain Album vs Item and file-sync conflict detection from Task 5 owns the file merge.

When no release provider contributes but a track provider does, still run track enrichment; the inverse also remains valid.

- [ ] **Step 5: Update public docs for only what Foundation actually delivers**

Document:

- `styles` is plural/lossless in the database; scalar `style` is a legacy read fallback.
- canonical v2 fields exist even when their semantic provider arrives in the next implementation change.
- `--write` general authority and the `--apply --write` ordinary form.
- legacy `--identity-tags --write` remains unchanged.
- `local_analysis` config exists but local BPM backend is not yet delivered by Foundation; state this explicitly so users are not promised an analyzer that is not present.
- MusicBrainz zero-credential default is enabled.

Do not document Cover Art Archive as active until the Artwork + Audio change implements it.

- [ ] **Step 6: Run focused docs/config/CLI tests**

```bash
pytest tests -q -k 'configuration or command or library_track or track_planning or field_types'
python scripts/validate_public_docs.py
mkdocs build --strict
```

Use the repository's exact documentation validation command if the script name differs; inspect CI/workflow before substituting.

- [ ] **Step 7: Run the full supported verification matrix locally where available**

```bash
ruff check .
pytest -q
python -m build
python -m twine check dist/*
```

Then run the repository's compatibility commands for beets `2.12.0` and latest `<3` exactly as CI defines them. Do not claim matrix coverage for interpreters/environments not actually executed locally; CI supplies the final matrix evidence.

- [ ] **Step 8: Review the final diff against Foundation scope**

Required final diff properties:

```text
ALLOWED
- Artist scope primitives
- provider registry multi-scope support
- typed v2 fields and plural style migration
- generalized track target/library Item support
- generic safe file sync and --write authority
- v2 Foundation config/docs/tests

NOT ALLOWED
- MusicBrainz Work/Artist semantic API implementation
- mood taxonomy implementation
- Cover Art Archive networking/download
- artwork embedding
- BPM provider or local analyzer backend
- [audio] dependency
- local ML mood analysis
- identity/AcoustID semantic changes
- version/tag/release publication
```

- [ ] **Step 9: Commit final integration/docs**

```bash
git add beetsplug/noqlenmeta/configuration.py beetsplug/noqlenmeta/resolver.py beetsplug/noqlenmeta/__init__.py site-docs/reference/fields.md site-docs/reference/configuration.md site-docs/reference/commands.md site-docs/examples/full-config.yaml tests
git commit -m "docs: document v2 foundation contracts"
```

- [ ] **Step 10: Final evidence before PR**

Record:

```text
- exact branch head SHA
- exact diff vs current main
- full pytest result
- Ruff result
- strict docs result
- package/twine result
- compatibility checks actually run
- remaining known risk: semantic providers/artwork/audio intentionally deferred
```

Open a PR only after the final diff contains no out-of-scope Semantic Enrichment or Artwork + Audio implementation.

---

## Plan Self-Review

### Foundation spec coverage

- Artist scope: Task 1.
- Provider architecture capable of the same service spanning release/track/artist: Task 1.
- Lossless multivalue persistence and legacy `style` migration: Task 2.
- Track enrichment generalized beyond lyrics: Task 3.
- Existing-library Item parity and shared track resolver/provider collection: Tasks 3 and 6.
- Generic file synchronization behind `--write`: Tasks 4 and 5.
- Database-first ordinary apply and explicit media-file authority: Task 5.
- v2 Foundation config/defaults without lying about CAA/audio implementations: Task 6.
- Identity and AcoustID isolation: global constraints plus Tasks 4-6 regression gates.
- No heavyweight base dependency: global constraints; `[audio]` remains deferred.

### Explicitly deferred to later approved v2 plans

- Semantic Enrichment: MusicBrainz Work language lookup, MusicBrainz Artist area/country, mood normalization, expanded Last.fm/Discogs semantics, derived artist languages.
- Artwork + Audio: CAA provider/download/sidecar/embed, custom MediaFile descriptors needed for final semantic tag sync, provider BPM, optional `[audio]` backend, local authority conflict handling.

### Placeholder scan

This plan contains no implementation `TODO`/`TBD` placeholders. Any conditional wording refers to repository-discovery mechanics (for example, using the existing command test module if present) rather than unresolved product behavior.

### Type consistency

- Canonical multi-text values remain `tuple[str, ...]` through domain/resolution/plans.
- Beets database/materialized values become list only at beets application boundaries using `MULTI_VALUE_DSV`.
- `bpm` is canonical `float` and uses the built-in beets Item field.
- `TrackTargetPlan` is shared by importer TrackInfo and persistent Item application.
- File sync consumes `PlannedChange` values but has its own snapshot/application result; it does not mutate resolver decisions.
