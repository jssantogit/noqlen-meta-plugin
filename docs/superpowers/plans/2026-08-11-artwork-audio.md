# Noqlen Meta v2 Artwork + Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved v2 Artwork + Audio phase: exact CAA album covers with safe sidecar/embedding behavior plus opt-in local BPM analysis through a lazy Librosa backend.

**Architecture:** Artwork gets a dedicated immutable plan/application pipeline beside ordinary metadata sync; CAA metadata selection occurs during planning and binary image download occurs only during `--apply`. BPM stays an ordinary canonical `float` field, but local evidence comes through a small `TempoAnalyzer` boundary whose only first implementation is lazy Librosa. Import and existing-library adapters share the same artwork/BPM policy, and `--write` authorizes only already-prepared media-file mutations.

**Tech Stack:** Python 3.10-3.14 base package, beets >=2.12,<3, MediaFile/mutagen through beets, requests, Librosa >=0.11,<1 as optional `[audio]` dependency, pytest, ruff, MkDocs.

## Global Constraints

- Branch: `feat/artwork-audio`.
- Integration base: `b333dead08b7671b9c151c2bacd2ee300dd16900`.
- Approved spec: `docs/superpowers/specs/2026-08-11-artwork-audio-design.md` at commit `62423c42c73129296ccd1f407ef0be0694b87cc8`.
- `fields.cover: true` and `fields.bpm: true` remain capability gates.
- Cover Art Archive is the only remote artwork provider in this phase and is enabled by default.
- Artwork lookup is exact Release first; Release Group is fallback only after definitive exact absence/no eligible approved main front.
- Transient exact CAA failure yields `UNAVAILABLE`; it must not trigger Release Group fallback.
- CAA image is eligible only when it is the API-defined `front == true` main front and `approved == true`.
- Artwork sizes are only `original`, `1200`, `500`, `250`; explicit thumbnail size is a maximum and never escalates upward.
- `original` non-JPEG falls back to CAA JPEG thumbnails `1200 -> 500 -> 250`; no local conversion/resizing/recompression/Pillow.
- Sidecar filename is always exactly `cover.jpg`, independent of global beets `art_filename`.
- `artwork.replace_existing` defaults to `false`; existing `cover.jpg` or any embedded art counts as curated artwork.
- If any track has embedded art and replacement is disabled, preserve the album as a whole; do not fill gaps.
- Existing `cover.jpg` with no embedded art is authoritative and may be embedded unchanged under `--apply --write` without CAA replacement.
- `artwork.replace_existing: true` makes the selected CAA front uniform across sidecars and, with `--write`, all album tracks.
- Artwork is album/Release-level only; singleton artwork is out of scope.
- Multidisc albums reuse one selected/downloaded payload and write identical `cover.jpg` bytes to each real disc directory.
- `--apply` may create/replace authorized sidecars and persist verified `Album.artpath`; `--write` is required for audio-file mutation/embedding.
- `--write` never causes a second CAA selection/download decision or triggers Librosa when the prepared plan did not require it.
- No external BPM provider in this phase.
- Librosa is the only local BPM backend; no backend registry or user-selectable backend system.
- Local BPM analysis defaults to disabled and Librosa must not import at plugin startup.
- BPM existing value is preserved by default; `bpm.recalculate_existing: true` explicitly enables recalculation when local analysis is enabled.
- BPM canonical value is `float`; optional rounding occurs before DB/file persistence.
- Full-track BPM analysis is default; optional `window` mode uses one centered window, default 90 seconds.
- Half/double-time normalization is off by default and, when enabled, uses only ×2/÷2 into configured range.
- One track's decoder/analyzer failure is local `UNAVAILABLE`; unrelated targets continue.
- Importer and existing-library paths must have the same artwork/BPM semantics.
- Preserve all Semantic Enrichment, Genre Foundation, identity, AcoustID, and ordinary file-sync behavior.
- Do not implement local ML mood analysis, secondary cover providers, fuzzy artwork search, multi-image artwork, or a version bump.
- CI compatibility remains base Python 3.10-3.14 and beets `2.12.0` / latest `<3`.

---

## File structure

Create focused files instead of enlarging `__init__.py` or `file_sync.py` with unrelated binary/audio logic:

```text
beetsplug/noqlenmeta/
├── artwork.py                 # artwork domain values, settings, pure planning/resolution
├── artwork_application.py     # bounded image bytes, sidecars, artpath, embedding, verification
├── tempo.py                   # BPM settings, normalization, TempoAnalyzer + lazy Librosa backend
└── providers/
    └── coverartarchive.py     # exact CAA HTTP/JSON boundary and candidate extraction
```

Existing integration points stay in:

```text
beetsplug/noqlenmeta/__init__.py
beetsplug/noqlenmeta/configuration.py
beetsplug/noqlenmeta/file_sync.py
pyproject.toml
.github/workflows/ci.yml
```

Primary new tests:

```text
tests/test_artwork.py
tests/test_artwork_application.py
tests/test_coverartarchive_provider.py
tests/test_tempo.py
tests/test_tempo_librosa.py
tests/test_artwork_audio_integration.py
```

---

### Task 1: Public config, artwork/BPM domain values, and optional audio packaging

**Files:**
- Create: `beetsplug/noqlenmeta/artwork.py`
- Create: `beetsplug/noqlenmeta/tempo.py`
- Modify: `beetsplug/noqlenmeta/configuration.py`
- Modify: `pyproject.toml`
- Create: `tests/test_artwork.py`
- Create: `tests/test_tempo.py`
- Modify: `tests/test_v2_foundation_command.py`
- Modify: `tests/test_plugin_loads.py`

**Interfaces produced:**

```python
class ArtworkSize(Enum):
    ORIGINAL = "original"
    PX_1200 = "1200"
    PX_500 = "500"
    PX_250 = "250"

@dataclass(frozen=True, slots=True)
class ArtworkSettings:
    size: ArtworkSize = ArtworkSize.ORIGINAL
    replace_existing: bool = False

@dataclass(frozen=True, slots=True)
class ArtworkCandidate:
    source_scope: str
    release_mbid: str
    release_group_mbid: str | None
    source_release_mbid: str | None
    image_id: str
    original_url: str
    thumbnail_urls: Mapping[int, str]
    requested_size: ArtworkSize
    effective_size: str
    selected_url: str
    original_mime_hint: str | None = None

@dataclass(frozen=True, slots=True)
class BpmSettings:
    round: bool = False
    recalculate_existing: bool = False
    octave_normalization: bool = False
    octave_min: float = 70.0
    octave_max: float = 180.0

@dataclass(frozen=True, slots=True)
class LocalBpmSettings:
    enabled: bool = False
    analysis_mode: str = "full"
    window_seconds: float = 90.0

@dataclass(frozen=True, slots=True)
class TempoObservation:
    bpm: float
    backend: str
```

- [ ] **Step 1: Write RED config/domain tests**

Assert exact default tree:

```python
assert config["providers"]["coverartarchive"] == {"enabled": True}
assert config["artwork"] == {"size": "original", "replace_existing": False}
assert config["bpm"] == {
    "round": False,
    "recalculate_existing": False,
    "octave_normalization": False,
    "octave_range": {"min": 70, "max": 180},
}
assert config["local_analysis"]["bpm"] == {
    "enabled": False,
    "analysis_mode": "full",
    "window_seconds": 90,
}
```

Reject `size: 1000`, booleans supplied as integers, `analysis_mode: start`, nonpositive/NaN/infinite window sizes, and octave ranges with `min >= max`.

Run:

```bash
pytest -q tests/test_artwork.py tests/test_tempo.py tests/test_v2_foundation_command.py
```

Expected: FAIL because the focused settings/classes are absent and current config still uses `mode: fallback`.

- [ ] **Step 2: Implement strict settings parsing/validation**

Keep public validation in `configuration.py`, but convert validated raw values to immutable settings in `artwork.py`/`tempo.py`.

Required pure helper signatures:

```python
def artwork_settings_from_config(value: object) -> ArtworkSettings: ...
def bpm_settings_from_config(value: object) -> BpmSettings: ...
def local_bpm_settings_from_config(value: object) -> LocalBpmSettings: ...
```

Do not accept unknown keys silently.

- [ ] **Step 3: Add the optional audio extra without importing it**

Add:

```toml
[project.optional-dependencies]
audio = [
    "librosa>=0.11,<1",
]
```

Do not add Librosa to base `dependencies` or the existing `dev` extra. `tests/test_plugin_loads.py` must prove importing `beetsplug.noqlenmeta` does not put `librosa` into `sys.modules`.

- [ ] **Step 4: Verify and commit**

```bash
pytest -q tests/test_artwork.py tests/test_tempo.py tests/test_v2_foundation_command.py tests/test_plugin_loads.py
ruff check beetsplug/noqlenmeta/artwork.py beetsplug/noqlenmeta/tempo.py beetsplug/noqlenmeta/configuration.py tests/test_artwork.py tests/test_tempo.py
git add beetsplug/noqlenmeta/artwork.py beetsplug/noqlenmeta/tempo.py beetsplug/noqlenmeta/configuration.py pyproject.toml tests/test_artwork.py tests/test_tempo.py tests/test_v2_foundation_command.py tests/test_plugin_loads.py
git commit -m "feat: add artwork and bpm configuration"
```

---

### Task 2: Exact Cover Art Archive metadata selection

**Files:**
- Create: `beetsplug/noqlenmeta/providers/coverartarchive.py`
- Modify: `beetsplug/noqlenmeta/artwork.py`
- Create: `tests/test_coverartarchive_provider.py`
- Modify: `tests/test_artwork.py`

**Interfaces produced:**

```python
class CoverArtArchiveError(RuntimeError): ...
class CoverArtArchiveUnavailable(CoverArtArchiveError): ...

class CoverArtArchiveClient:
    def get_release(self, release_mbid: str) -> Mapping[str, object] | None: ...
    def get_release_group(self, release_group_mbid: str) -> Mapping[str, object] | None: ...

@dataclass(frozen=True, slots=True)
class ArtworkLookupResult:
    outcome: str
    candidate: ArtworkCandidate | None = None
    reason: str | None = None


def resolve_caa_artwork(
    client: CoverArtArchiveClient,
    *,
    release_mbid: str,
    release_group_mbid: str | None,
    settings: ArtworkSettings,
) -> ArtworkLookupResult: ...
```

- [ ] **Step 1: Write RED exact-release selection tests**

Use sanitized inline JSON fixtures with:

```python
{
    "images": [{
        "id": "123",
        "front": True,
        "approved": True,
        "image": "https://coverartarchive.org/release/.../123.jpg",
        "thumbnails": {
            "250": "https://coverartarchive.org/release/.../123-250.jpg",
            "500": "https://coverartarchive.org/release/.../123-500.jpg",
            "1200": "https://coverartarchive.org/release/.../123-1200.jpg",
        },
    }],
    "release": "https://musicbrainz.org/release/<exact-mbid>",
}
```

Assert:

```text
front=true + approved=true -> selected
front=false -> ignored
approved=false main front -> no eligible exact candidate
response release MBID mismatch -> unavailable/invalid, never accepted
no custom voting/count ordering fields are consulted
```

- [ ] **Step 2: Write RED fallback/error tests**

Required call-counter outcomes:

```text
exact candidate exists -> RG call count 0
exact 404/None -> RG may run
exact valid JSON but no approved main front -> RG may run
exact timeout/network/5xx -> UNAVAILABLE, RG call count 0
exact malformed JSON/identity -> UNAVAILABLE, RG call count 0
exact absent + RG absent -> NO_EVIDENCE
exact absent + RG transient failure -> UNAVAILABLE
```

Release Group provenance must retain the source Release URL/MBID supplied by CAA.

- [ ] **Step 3: Write RED native-size tests**

Pure size-selection cases:

```text
original JPEG -> original URL
original PNG/WebP hint -> 1200 then 500 then 250 JPEG thumbnail
1200 requested -> 1200 else 500 else 250
500 requested -> 500 else 250
250 requested -> 250 only
500 requested with only 1200 -> no eligible representation
```

For an original URL without a trustworthy JPEG extension/content hint, allow planning to choose `original` provisionally; binary validation in Task 3 decides whether it is JPEG and can fall back to the preplanned CAA thumbnail URLs without a new provider lookup.

- [ ] **Step 4: Implement the CAA boundary**

Use the project's existing HTTP style (`requests` through an injectable session/client boundary). Exact requirements:

```text
connect/read timeout is finite
404 -> definitive None
5xx/request exception -> CoverArtArchiveUnavailable
JSON object shape validated before candidate extraction
response identity validated
only front==true and approved==true is eligible
```

No binary image download belongs in this client method.

- [ ] **Step 5: Verify and commit**

```bash
pytest -q tests/test_coverartarchive_provider.py tests/test_artwork.py
ruff check beetsplug/noqlenmeta/providers/coverartarchive.py beetsplug/noqlenmeta/artwork.py tests/test_coverartarchive_provider.py tests/test_artwork.py
git add beetsplug/noqlenmeta/providers/coverartarchive.py beetsplug/noqlenmeta/artwork.py tests/test_coverartarchive_provider.py tests/test_artwork.py
git commit -m "feat: add Cover Art Archive selection"
```

---

### Task 3: Artwork planning, sidecars, artpath, and verified embedding

**Files:**
- Create: `beetsplug/noqlenmeta/artwork_application.py`
- Modify: `beetsplug/noqlenmeta/artwork.py`
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Create: `tests/test_artwork_application.py`
- Create: `tests/test_artwork_audio_integration.py`
- Modify: `tests/test_beets_integration.py`

**Interfaces produced:**

```python
@dataclass(frozen=True, slots=True)
class ArtworkContext:
    album_id: int
    release_mbid: str
    release_group_mbid: str | None
    item_ids: tuple[int, ...]
    item_paths: tuple[bytes, ...]
    disc_directories: tuple[bytes, ...]
    existing_sidecars: tuple[bytes, ...]
    embedded_art_item_ids: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class ArtworkPlan:
    album_id: int
    outcome: str
    candidate: ArtworkCandidate | None
    local_source: bytes | None
    sidecar_destinations: tuple[bytes, ...]
    canonical_artpath: bytes | None
    embed_item_ids: tuple[int, ...]
    replace_existing: bool
    reason: str | None = None

@dataclass(frozen=True, slots=True)
class ArtworkApplicationResult:
    album_id: int
    committed_sidecars: tuple[bytes, ...] = ()
    embedded_item_ids: tuple[int, ...] = ()
    artpath_committed: bool = False
    blocked_reason: str | None = None
    state_uncertain: bool = False
    recovery_artifact_retained: bool = False
```

Primary pure planner:

```python
def plan_album_artwork(
    album: Album,
    items: Sequence[Item],
    lookup: ArtworkLookupResult | None,
    settings: ArtworkSettings,
    *,
    write_enabled: bool,
) -> ArtworkPlan: ...
```

- [ ] **Step 1: Write RED preservation/planning tests**

Cover exactly:

```text
cover.jpg exists + no embedded art + replace=false -> local source, no CAA replacement
any embedded art + replace=false -> preserve whole album, no gap filling
no existing art + CAA candidate -> sidecar plan
replace=true + CAA candidate -> sidecar replacement plan
replace=true + write=true -> every persisted album item becomes embed target
write=false -> embed target tuple empty
singleton/no Album -> no artwork plan
```

Multidisc test: paths under `CD1/` and `CD2/` produce `CD1/cover.jpg` and `CD2/cover.jpg`, one canonical artpath, and one candidate/payload identity.

- [ ] **Step 2: Write RED binary validation/download tests**

In `artwork_application.py`, expose small injectable boundaries:

```python
MAX_ARTWORK_BYTES = 50 * 1024 * 1024


def download_artwork(candidate: ArtworkCandidate, session, *, max_bytes: int = MAX_ARTWORK_BYTES) -> bytes: ...
def validate_jpeg_bytes(payload: bytes) -> None: ...
```

Tests must prove:

```text
stream exceeds max -> reject before sidecar mutation
empty payload -> reject
non-JPEG original -> use preplanned 1200/500/250 JPEG URL fallback in order without new CAA metadata lookup
invalid final JPEG -> reject
redirects can resolve away from coverartarchive.org but redirect count remains bounded by HTTP client policy
```

Basic JPEG validation must at minimum check SOI/EOI markers and that the payload can be handed to the MediaFile embedding path used by the supported formats; do not add Pillow solely for validation.

- [ ] **Step 3: Implement atomic `cover.jpg` application and `Album.artpath` commit**

Required order:

```text
preflight every sidecar destination
→ obtain/validate payload once
→ create fsynced temp file beside each destination
→ verify temp digest == payload digest
→ atomic os.replace for authorized destinations
→ reopen/read and verify final digest
→ only after verified sidecars: set/store canonical Album.artpath
```

If replacement is disabled, re-check destination nonexistence immediately before replace to avoid clobbering a sidecar created after preview.

Do not call `Album.set_art()` as the writer because its destination follows global `art_filename`; Noqlen owns exact `cover.jpg` destinations. Persist only the verified path into the Album database model.

- [ ] **Step 4: Implement verified media embedding**

Reuse the `file_sync.py` safety pattern, not the generic tag-change type:

```text
snapshot source MediaFile + filesystem metadata
→ candidate copy
→ set one front-cover image from exact validated JPEG bytes
→ save candidate
→ reopen candidate and verify exactly one managed primary front payload matches digest
→ atomic replace with recovery artifact
→ reopen final media file and verify
→ update beets item mtime/store only after verified commit
```

When `replace_existing: true`, replace managed embedded images with the selected one. When local `cover.jpg` is authoritative under default preservation, embed those exact bytes into all album tracks only when no track had embedded art at plan time.

Use existing beets/MediaFile image primitives; do not enable or depend on the beets `embedart` plugin.

- [ ] **Step 5: Integrate library preview/apply without changing provider collection on `--write`**

In `__init__.py`, prepare artwork alongside album plans only when `fields.cover` and `providers.coverartarchive.enabled` allow it or when local existing artwork can produce a synchronization plan. Render artwork effects separately from ordinary metadata/file-tag effects.

Add a test that runs the same target with/without `--write` using CAA call counters and proves metadata lookup count and selected candidate are identical; only embed destinations differ.

- [ ] **Step 6: Verify and commit**

```bash
pytest -q tests/test_artwork.py tests/test_coverartarchive_provider.py tests/test_artwork_application.py tests/test_artwork_audio_integration.py tests/test_beets_integration.py
ruff check beetsplug/noqlenmeta/artwork.py beetsplug/noqlenmeta/artwork_application.py beetsplug/noqlenmeta/providers/coverartarchive.py beetsplug/noqlenmeta/__init__.py tests/test_artwork_application.py tests/test_artwork_audio_integration.py
git add beetsplug/noqlenmeta/artwork.py beetsplug/noqlenmeta/artwork_application.py beetsplug/noqlenmeta/providers/coverartarchive.py beetsplug/noqlenmeta/__init__.py tests/test_artwork_application.py tests/test_artwork_audio_integration.py tests/test_beets_integration.py
git commit -m "feat: apply and embed verified album artwork"
```

---

### Task 4: Lazy Librosa BPM analyzer and pure tempo policy

**Files:**
- Modify: `beetsplug/noqlenmeta/tempo.py`
- Create: `tests/test_tempo_librosa.py`
- Modify: `tests/test_tempo.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces produced:**

```python
class TempoAnalysisUnavailable(RuntimeError): ...

class TempoAnalyzer(Protocol):
    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation: ...

class LibrosaTempoAnalyzer:
    def analyze(self, path: bytes, settings: LocalBpmSettings) -> TempoObservation: ...


def normalize_bpm(observation: TempoObservation, settings: BpmSettings) -> float: ...
```

- [ ] **Step 1: Write RED pure normalization tests**

Required exact cases:

```python
assert normalize(127.63, default) == 127.63
assert normalize(127.63, round=True) == 128.0
assert normalize(55.0, octave=True, 70..180) == 110.0
assert normalize(210.0, octave=True, 70..180) == 105.0
assert normalize(72.0, octave=True, 70..180) == 72.0
assert normalize(144.0, octave=True, 70..180) == 144.0
```

Reject nonfinite, zero, and negative analyzer BPM. Octave normalization runs before rounding and uses only repeated ×2/÷2 operations.

- [ ] **Step 2: Write RED lazy-import tests with a fake Librosa module**

Before `analyze()`:

```python
assert "librosa" not in sys.modules
```

Inject a fake import/module exposing `load`, `get_duration`, and `beat.beat_track`; call `analyze()` and assert the module is requested only then.

Mono `beat_track()` in Librosa 0.11 may return a one-element ndarray; convert only a scalar/one-element result to `float` and reject ambiguous multi-value results.

A returned `0 BPM` is `TempoAnalysisUnavailable`, not valid evidence.

- [ ] **Step 3: Implement `full` and centered `window` modes**

Full mode:

```python
y, sr = librosa.load(path_str)
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
```

Window mode:

```python
duration = float(librosa.get_duration(path=path_str))
window = min(settings.window_seconds, duration)
offset = max(0.0, (duration - window) / 2.0)
y, sr = librosa.load(path_str, offset=offset, duration=window)
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
```

Do not add multiple-window heuristics or custom tempo priors.

Wrap import/decode/analysis failures as `TempoAnalysisUnavailable` with a stable user-facing reason; preserve original exception chaining for logs/tests.

- [ ] **Step 4: Add one real `[audio]` CI lane**

Do not burden all Python 3.10-3.14 base jobs with Librosa. Add a focused job on Python 3.13:

```yaml
audio-analysis:
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-python@v6
      with:
        python-version: "3.13"
        cache: pip
    - run: python -m pip install -e ".[audio,dev]"
    - run: pytest -q tests/test_tempo.py tests/test_tempo_librosa.py
```

`tests/test_tempo_librosa.py` must include at least one tiny deterministic generated/fixture click-track case with a broad realistic tolerance; do not assert an exact floating BPM from DSP.

- [ ] **Step 5: Verify and commit**

```bash
pytest -q tests/test_tempo.py
ruff check beetsplug/noqlenmeta/tempo.py tests/test_tempo.py tests/test_tempo_librosa.py
python -m pip install -e ".[audio]"
pytest -q tests/test_tempo.py tests/test_tempo_librosa.py
git add beetsplug/noqlenmeta/tempo.py tests/test_tempo.py tests/test_tempo_librosa.py .github/workflows/ci.yml
git commit -m "feat: add optional Librosa bpm analysis"
```

---

### Task 5: BPM import/library planning, DB persistence, and file sync

**Files:**
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `beetsplug/noqlenmeta/file_sync.py`
- Modify: `tests/test_file_sync.py`
- Modify: `tests/test_artwork_audio_integration.py`
- Modify: `tests/test_beets_integration.py`
- Modify: `tests/test_library_cli.py`

**Interfaces produced:**

```python
@dataclass(frozen=True, slots=True)
class BpmPlanningResult:
    outcome: str
    current_bpm: float | None
    observation: TempoObservation | None
    canonical_bpm: float | None
    reason: str | None = None


def plan_bpm(
    *,
    path: bytes,
    existing_bpm: object,
    field_enabled: bool,
    bpm_settings: BpmSettings,
    local_settings: LocalBpmSettings,
    analyzer: TempoAnalyzer | None,
) -> BpmPlanningResult: ...
```

- [ ] **Step 1: Write RED preservation/recalculation tests**

Call-counter requirements:

```text
fields.bpm=false -> analyzer 0 calls
existing BPM + recalculate=false -> PRESERVED, analyzer 0 calls
missing BPM + local enabled=false -> no analyzer call/no evidence
missing BPM + local enabled=true -> analyzer 1 call
existing BPM + recalculate=true + local enabled=true -> analyzer 1 call
existing BPM + recalculate=true + local enabled=false -> preserve existing; no destructive clearing
analyzer unavailable -> UNAVAILABLE for this track only
```

- [ ] **Step 2: Integrate analyzed BPM as canonical planned metadata**

When analysis resolves a canonical value, feed it through the same track change/application architecture used by other canonical fields. Do not create a second DB mutation path solely for BPM.

`--apply` stores the canonical BPM in the beets Item database. Preview without apply must never store it.

The analyzer runs because the prepared enrichment configuration requested local BPM—not because `--write` was added.

- [ ] **Step 3: Prove existing DB BPM can synchronize without analysis**

The existing `file_sync.py` already maps canonical `bpm` to MediaFile scalar float. Add a planning path/test where DB BPM is `128.0`, media tag is absent/different, `recalculate_existing=false`, and `--write` produces a file-sync change from the approved DB value with analyzer call count `0`.

Do not change `FILE_TAG_TARGETS["bpm"]` away from `SCALAR_FLOAT` unless a real supported MediaFile format test proves the current mapping cannot round-trip.

- [ ] **Step 4: Add importer/library parity tests**

Shared scenarios:

```text
missing BPM + local enabled -> same canonical value in importer and library plan
existing BPM default -> both preserve without analyzer
recalculate=true -> both replace under apply
one failed track -> sibling track/artwork/metadata plans continue
round=true -> DB and written MediaFile expose same canonical value
```

For import timing, analyze the actual selected source/final accessible audio path already used by the importer adapter; do not invent a separate pre-import temporary metadata store. Ensure application occurs at a lifecycle point where the final Item DB/file target is valid and test it with the existing importer harness.

- [ ] **Step 5: Verify and commit**

```bash
pytest -q tests/test_tempo.py tests/test_file_sync.py tests/test_artwork_audio_integration.py tests/test_beets_integration.py tests/test_library_cli.py
ruff check beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/file_sync.py beetsplug/noqlenmeta/tempo.py tests/test_artwork_audio_integration.py
git add beetsplug/noqlenmeta/__init__.py beetsplug/noqlenmeta/file_sync.py beetsplug/noqlenmeta/tempo.py tests/test_file_sync.py tests/test_artwork_audio_integration.py tests/test_beets_integration.py tests/test_library_cli.py
git commit -m "feat: integrate bpm enrichment and file sync"
```

---

### Task 6: Import parity for artwork, public docs, and integrated verification

**Files:**
- Modify: `beetsplug/noqlenmeta/__init__.py`
- Modify: `tests/test_artwork_audio_integration.py`
- Modify: `tests/test_beets_integration.py`
- Modify: `README.md`
- Modify: `site-docs/reference/configuration.md`
- Modify: `site-docs/reference/fields.md`
- Modify: `site-docs/reference/providers.md`
- Modify: `site-docs/reference/commands.md`
- Modify: `site-docs/reference/beets-interaction.md`
- Modify: `docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md`
- Modify: `tests/docs/test_public_docs.py` or the existing public-doc contract tests used by `scripts/check_public_docs.py`

- [ ] **Step 1: Finish artwork importer parity**

Use the same `ArtworkContext`, CAA resolver, preservation policy, and application functions as the library command. The importer adapter may delay sidecar path materialization until final album paths exist, but it must not reselect a different CAA image.

Test:

```text
same Release/RG fixture -> importer and library choose same candidate/source scope/effective size
--apply import -> verified cover.jpg + Album.artpath
--apply --write import -> same + identical embedded bytes across album tracks
existing local art under preserve policy -> no CAA overwrite
multidisc import -> each final disc directory gets identical cover.jpg
```

- [ ] **Step 2: Update the umbrella v2 design so examples are no longer stale**

Change only Artwork/BPM-specific illustrative sections to match the focused spec:

```yaml
providers:
  coverartarchive:
    enabled: true

artwork:
  size: original
  replace_existing: false

bpm:
  round: false
  recalculate_existing: false
  octave_normalization: false
  octave_range:
    min: 70
    max: 180

local_analysis:
  bpm:
    enabled: false
    analysis_mode: full
    window_seconds: 90
```

Remove the old `mode: fallback` illustration and do not claim an external BPM provider was implemented.

- [ ] **Step 3: Update public documentation contract**

Document:

```text
CAA exact Release -> RG fallback semantics
approved main-front requirement
cover.jpg fixed filename
size/native JPEG behavior
preserve vs replace_existing behavior
--apply sidecar vs --apply --write embedding
multidisc behavior
[audio] installation
local BPM disabled by default
full/window, round, recalculate, octave normalization
local BPM failure isolation
no external BPM provider in this v2 cut
```

Ensure docs never imply that `--write` itself downloads a different cover or starts BPM analysis.

- [ ] **Step 4: Run focused integrated verification**

Without audio extra:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest -m "not live"
python scripts/check_repo_contamination.py
python scripts/check_public_docs.py
mkdocs build --strict
python -m build
python -m twine check --strict dist/*
python scripts/check_distribution.py dist
```

With audio extra:

```bash
python -m pip install -e ".[audio]"
pytest -q tests/test_tempo.py tests/test_tempo_librosa.py tests/test_artwork_audio_integration.py
```

Expected: all commands exit 0.

- [ ] **Step 5: Run explicit outcome smoke tests**

Create temporary beets libraries/media fixtures only; never a real user library. Verify observable files after commands:

```text
preview -> no DB/sidecar/media mutation
--apply -> DB + authorized cover.jpg/artpath, no embedding/media BPM tag mutation
--apply --write -> same DB/sidecar plan + verified embedded art/BPM tags
write vs no-write planning -> same CAA candidate and same analyzed BPM evidence
```

- [ ] **Step 6: Commit final phase integration**

```bash
git add beetsplug/noqlenmeta/__init__.py tests/test_artwork_audio_integration.py tests/test_beets_integration.py README.md site-docs docs/superpowers/specs/2026-08-10-noqlen-meta-v2-design.md .github/workflows/ci.yml pyproject.toml
git commit -m "docs: complete artwork and audio integration"
```

Do not bump `version = "1.0.0"` in this task. Versioning/release readiness happens only after this feature is reviewed and merged into the v2 integration branch.

---

## Final self-review gate

Before requesting merge/review, map every focused spec section to implemented tests and confirm no placeholder capability is advertised:

```text
Artwork architecture/CAA selection        -> Tasks 2-3
Size policy                               -> Tasks 2-3
Preserve/replace/local-sidecar semantics  -> Task 3
Multidisc/artpath/embed verification      -> Tasks 3, 6
BPM packaging/config                      -> Tasks 1, 4
Full/window Librosa                       -> Task 4
Round/recalculate/octave policy           -> Tasks 4-5
Import/library parity                     -> Tasks 5-6
Failure isolation                         -> Tasks 2-5
Docs/umbrella design alignment            -> Task 6
```

Run the complete offline suite after the final commit and inspect the actual branch diff against `docs/v2-enrichment-design`. Do not claim completion from earlier task-local runs.

## Execution handoff

Preferred execution for this repository: OpenCode implements the plan task-by-task on `feat/artwork-audio`; ChatGPT/Superpowers then performs the final diff, test/CI, and architecture verification before any merge into `docs/v2-enrichment-design`.
