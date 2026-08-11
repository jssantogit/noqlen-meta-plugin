# Noqlen Meta v2 Artwork + Audio Design

Status: approved product design for the final v2 enrichment phase before integrated release-readiness work.

This phase is built on `docs/v2-enrichment-design` after Semantic Enrichment merge `b333dead08b7671b9c151c2bacd2ee300dd16900`. Where illustrative defaults in the older umbrella v2 design conflict with this focused design, this document is authoritative for Artwork + Audio.

## Objective

Finish the first v2 enrichment architecture with two owned capabilities:

1. album-level front-cover artwork from the Cover Art Archive, including deterministic sidecars and optional embedding; and
2. optional local BPM analysis from the user's own audio files through a lazy Librosa backend.

Both capabilities must follow the existing Noqlen safety model: collect/prepare first, preview before mutation, apply database/sidecar changes only under `--apply`, mutate media files only under `--apply --write`, verify observable outcomes, and fail locally when the capability can safely be skipped.

## Non-goals

- No secondary artwork provider in this phase.
- No fuzzy artwork identity search.
- No track/single-specific artwork pipeline; artwork is album/Release-level only.
- No Back, Booklet, Disc, Medium, or multi-image embedding.
- No local image resizing, recompression, or Pillow dependency.
- No dependency on beets `fetchart`, `embedart`, or `autobpm` plugins.
- No external BPM provider in the first v2 implementation.
- No multiple audio-analysis backends or backend-selection framework.
- No local ML mood analysis.
- No v2 version bump or release in this feature branch.

---

## 1. Artwork architecture

Artwork remains a dedicated binary/image pipeline rather than a special `MetadataCandidate` or ordinary `FileSyncPlan` field.

```text
Album / Release identity
        ↓
ArtworkContext
  release MBID
  release-group MBID?
  album/item paths
  existing sidecar/embedded state
        ↓
CoverArtArchiveProvider
        ↓
ArtworkCandidate
  provider
  source_scope: release | release_group
  release_mbid
  release_group_mbid?
  source_release_mbid?
  image_id
  original_url
  thumbnail_urls
  requested_size
  effective_size
  mime_type?
  provenance
        ↓
Artwork resolver
        ↓
ArtworkPlan
  outcome
  candidate?
  local_source?
  sidecar_destinations[]
  canonical_artpath?
  embed_targets[]
  replace_existing
        ↓
preview
        ↓
--apply
  download/read once
  validate once
  write/verify cover.jpg
  persist Album.artpath
        ↓
--apply --write
  same prepared artwork
  + embed exact same bytes into every eligible album track
  + reopen/verify each media file
```

Provider metadata collection and artwork selection happen during plan preparation. The binary image is not downloaded during preview. Binary download happens only when an already-prepared plan is applied. Adding `--write` must not trigger another CAA lookup, another selection pass, or a different image download.

### Artwork domain boundary

Use focused immutable values rather than extending normal metadata values with image-specific fields. The exact class names may follow project naming conventions, but the responsibilities are fixed:

- `ArtworkContext`: exact Release identity, optional Release Group identity, album/item paths, and existing artwork state.
- `ArtworkCandidate`: one selected CAA front candidate plus provenance and native size URLs.
- `ArtworkPlan`: resolved action, source, destinations, embedding targets, and prepared preservation/replacement semantics.
- `ArtworkApplicationResult`: explicit committed/blocked/unavailable outcome and verification state.

Artwork should reuse the safety philosophy of `file_sync.py`—snapshot/preflight, temporary candidate, atomic replace, reopen/verify, recovery when needed—without forcing image bytes into the ordinary tag-sync abstraction.

---

## 2. Cover Art Archive authority and selection

Cover Art Archive is the only remote artwork provider in this phase and is enabled by default without credentials.

Lookup order is strict:

```text
exact MusicBrainz Release
→ if definitively absent/no eligible approved main front: Release Group fallback
→ otherwise stop
```

Never reverse the order. Release Group fallback must be visible in preview/provenance because it can represent a different edition.

### Eligible front

For a successful CAA JSON response, the eligible image is the CAA `front == true` main front and it must also have `approved == true`. The `front` flag is the CAA-defined main front returned by the `/front` endpoint; Noqlen does not invent vote counts, popularity ranking, or a custom order among images.

If the exact Release has no approved main front, that is treated as no eligible exact-release artwork and Release Group fallback may run.

### Absence versus transient failure

Fallback is allowed only after definitive absence/no eligible art.

```text
exact Release 404 / confirmed no eligible approved main front
→ Release Group may be attempted

network error / timeout / 5xx / malformed or invalid response
→ UNAVAILABLE
→ do not use Release Group as a substitute for a transient exact-release failure

Release + Release Group definitively have no eligible front
→ NO_EVIDENCE

exact Release absent + Release Group transient failure
→ UNAVAILABLE
```

Unrelated metadata enrichment continues when artwork is `NO_EVIDENCE` or `UNAVAILABLE`.

---

## 3. Artwork size policy

Public configuration:

```yaml
artwork:
  size: original
  replace_existing: false
```

Allowed `size` values:

```text
original | 1200 | 500 | 250
```

Noqlen uses only CAA-native original/thumbnail representations. There is no local resizing or recompression.

### `original`

- original JPEG → use original;
- original non-JPEG → use the largest available CAA JPEG thumbnail in order `1200 -> 500 -> 250`;
- no local format conversion;
- sidecar name remains exactly `cover.jpg`.

The preview reports when a non-JPEG original caused a JPEG-thumbnail fallback.

### Explicit thumbnail size

Configured thumbnail size is a maximum, not a target that may silently grow.

```text
size: 1200 → 1200, else 500, else 250
size: 500  → 500, else 250
size: 250  → 250 only
```

Noqlen never selects a larger representation than the explicit configured maximum. If no representation at or below the requested native size is available, the artwork representation is not eligible for application rather than silently escalating to a larger file.

---

## 4. Existing artwork and replacement semantics

Default behavior preserves user-curated artwork.

Artwork counts as existing if either:

- an album `cover.jpg` exists; or
- any track in the album already has embedded artwork.

With `artwork.replace_existing: false`:

- existing artwork is never automatically replaced by CAA;
- if any album track has embedded artwork, the whole album is treated as curated and Noqlen does not fill missing embedded-art gaps on other tracks;
- if `cover.jpg` exists and no track has embedded art, that local `cover.jpg` is authoritative for the album;
- under `--apply --write`, the authoritative local `cover.jpg` may be embedded unchanged into every album track without consulting/replacing it through CAA.

With `artwork.replace_existing: true`:

- the selected CAA front becomes the uniform album cover;
- `--apply` replaces/creates the album sidecar(s) and updates `Album.artpath` but does not mutate audio files;
- `--apply --write` also replaces existing embedded artwork and embeds the exact same selected bytes into every eligible track;
- there is no separate `sync_album_art` option.

`replace_existing` is persistent configuration only. Do not add a `--replace-artwork` CLI flag.

---

## 5. Sidecar, multidisc, Album.artpath, and embedding

The sidecar filename is always exactly:

```text
cover.jpg
```

Noqlen owns deterministic `cover.jpg` writing rather than delegating the filename decision to global beets `art_filename` configuration.

### Single-directory album

`--apply` writes `cover.jpg` atomically if the plan authorizes creation/replacement, verifies the final bytes, and persists the verified canonical sidecar path to `Album.artpath` through the beets database boundary.

### Multidisc album

All discs belonging to the same exact Release use one selected front and one downloaded/read byte payload.

- reuse the exact same bytes for every disc;
- create/replace `cover.jpg` in each actual disc directory where the plan requires it;
- do not refetch or reselect per disc;
- `Album.artpath` points to one canonical verified sidecar representation.

### Embedded artwork

Only one primary front image is managed per media file. Under `--apply --write`, the same validated bytes are embedded into all eligible album tracks and then each file is reopened to verify the observable embedded-art result.

Singletons/unassociated tracks are outside artwork scope in this phase.

---

## 6. Artwork download and mutation safety

Artwork application is bounded and transactional in spirit:

1. verify the prepared plan is still current;
2. download the selected CAA representation once, or read the authoritative local `cover.jpg` once;
3. enforce a finite internal byte limit before committing any mutation;
4. validate HTTP result, expected image representation, JPEG basic integrity, and non-empty payload;
5. materialize temporary sidecars before atomic replacement;
6. verify final sidecar bytes before updating `Album.artpath`;
7. for `--write`, mutate each media file through the same candidate-copy/reopen verification philosophy used by ordinary file sync;
8. report uncertain state/recovery artifacts explicitly if a post-commit verification fails.

The implementation may use a small internal safety constant for maximum download bytes. Do not add configuration for it in this phase unless implementation evidence shows a fixed safe bound cannot support legitimate CAA originals.

CAA redirects are an expected part of the API and may resolve to Internet Archive storage; redirect handling must remain bounded and must not assume the final host stays `coverartarchive.org`.

---

## 7. BPM architecture

The first v2 BPM implementation uses only local audio analysis. There is no external BPM provider in this phase.

The core does not depend directly on Librosa objects:

```text
file path
   ↓
TempoAnalyzer.analyze(path, settings)
   ↓
TempoObservation
  bpm: float
  backend: "librosa"
   ↓
BPM resolver/policy
   ↓
canonical bpm: float
   ↓
DB application
   ↓ --write
MediaFile BPM tag sync + reopen verification
```

The first and only backend is `LibrosaTempoAnalyzer`. Keep the `TempoAnalyzer` boundary small enough that a future backend can replace Librosa without changing resolution/persistence, but do not build a backend registry or user-selectable multi-backend framework now.

Librosa is an optional dependency and must be imported lazily only when local BPM analysis is actually requested.

Package installation shape:

```text
pip install beets-noqlenmeta
→ base plugin; no Librosa dependency/import

pip install "beets-noqlenmeta[audio]"
→ base plugin + supported Librosa dependency
```

---

## 8. BPM configuration and defaults

`fields.bpm` remains the capability gate. Local calculation is opt-in by default.

Target configuration:

```yaml
fields:
  bpm: true

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
  mood:
    enabled: false
```

The old inert `local_analysis.bpm.mode: fallback` key is removed. With no external BPM provider in this implementation, that key has no useful semantic role.

Validation is strict and happens before analysis:

- `round`, `recalculate_existing`, `octave_normalization`, and `enabled` are real booleans only;
- `analysis_mode` is exactly `full` or `window`;
- `window_seconds` is a finite positive numeric duration;
- octave range bounds are finite positive numbers with `min < max`;
- unknown keys are rejected consistently with current strict config validation.

---

## 9. BPM preservation, calculation, and synchronization

### Existing BPM

Default behavior preserves existing BPM.

```text
BPM already present
+ recalculate_existing: false
→ PRESERVED
→ do not call Librosa
```

Preservation means “do not recalculate or replace”, not “leave database and file tags divergent”. If the database already contains the approved BPM and the media file lacks/differs from that BPM, `--apply --write` may synchronize the approved database value to the file without calling Librosa.

### Recalculation

With:

```yaml
bpm:
  recalculate_existing: true
```

and local BPM analysis enabled, Librosa recalculates even when BPM already exists. The resolved value replaces the old value only under `--apply`; `--apply --write` also synchronizes the resulting canonical BPM to the file.

### Missing BPM

With `fields.bpm: true`, local analysis disabled, and no existing BPM, no analysis runs and the field remains without evidence.

With local analysis enabled and BPM absent, Librosa analyzes the file and produces a local observation when possible.

### Numeric representation

Canonical BPM remains `float`.

Default:

```text
127.63 → 127.63
```

With `bpm.round: true`, rounding occurs before persistence so database and file receive the same canonical integral-valued float:

```text
127.63 → 128.0
127.31 → 127.0
```

Do not keep a decimal database value while writing a different integer value to the media file.

---

## 10. Full versus windowed analysis

Default mode analyzes the full track:

```yaml
local_analysis:
  bpm:
    enabled: true
    analysis_mode: full
```

Optional window mode analyzes one centered window:

```yaml
local_analysis:
  bpm:
    enabled: true
    analysis_mode: window
    window_seconds: 90
```

Rules:

- `full` decodes/analyzes the full track;
- `window` uses one centered window only;
- if the track duration is shorter than `window_seconds`, analyze the full track;
- do not add “start”, “intro”, “three windows”, “best section”, or other heuristics in this phase.

The purpose of `window` is an explicit performance/accuracy tradeoff, not a different resolver.

---

## 11. Optional half/double-time normalization

The raw Librosa result is preserved by default. Noqlen does not silently decide that a plausible 72 BPM observation should be 144 BPM or vice versa.

With:

```yaml
bpm:
  octave_normalization: true
  octave_range:
    min: 70
    max: 180
```

Noqlen may normalize only by powers of two needed to bring a positive finite BPM into the configured interval:

```text
55  → 110
210 → 105
72  → 72
144 → 144
```

Do not apply arbitrary multipliers, genre-specific tempo priors, or hidden tempo-range bias in this phase.

Normalization occurs before optional rounding and before persistence.

---

## 12. Import and existing-library parity

Artwork and BPM share one core behavior across importer and existing-library paths.

### Artwork

Only album/Release targets participate. Both paths use the same exact Release → Release Group fallback, size, preservation, sidecar, replacement, and embedding policy. Application adapters may differ because final import paths/database timing differ, but user-visible semantics must not.

### BPM

Both paths use the same:

- existing-value preservation;
- optional recalculation;
- Librosa analyzer;
- full/window settings;
- octave normalization;
- rounding;
- local failure outcomes;
- `--write` file-tag synchronization.

Do not implement local BPM analysis for library commands while leaving the importer on a separate or deferred algorithm.

---

## 13. Failure outcomes

Use the existing explicit outcome vocabulary where it fits:

- `RESOLVED`: usable artwork/BPM plan exists;
- `NO_EVIDENCE`: provider/analyzer definitively has no usable evidence;
- `UNAVAILABLE`: transient provider failure, optional audio backend absent, decoder failure, or analyzer failure;
- `BLOCKED`: structural/configuration/mutation-safety condition prevents a requested action;
- `CONFLICT`: only if future evidence introduces genuinely equal incompatible authorities; the first CAA-only/local-BPM path should not manufacture conflicts.

Examples:

```text
CAA 404 on Release + 404/no eligible Release Group → NO_EVIDENCE
CAA timeout/5xx/invalid JSON → UNAVAILABLE
Librosa extra missing while local BPM enabled → UNAVAILABLE for BPM only
one track cannot decode → UNAVAILABLE for that track's BPM only
stale file/artwork snapshot before mutation → BLOCKED / application error
invalid downloaded JPEG → BLOCKED before sidecar/embed mutation
```

One track's BPM analysis failure must not abort the album import/library command or unrelated metadata/artwork work.

---

## 14. Preview and authority model

Preview must make expensive/binary/file effects understandable without mutating state.

Artwork preview reports at least:

- outcome;
- exact Release versus Release Group source;
- requested and effective size;
- existing artwork preservation or configured replacement;
- sidecar destinations;
- canonical artpath target;
- number of embed targets if `--write` is prepared;
- local `cover.jpg` authority when used instead of CAA.

BPM preview reports at least:

- existing/preserved versus analyzed source;
- raw local BPM when analysis ran;
- octave-normalized BPM when enabled;
- final rounded/unrounded canonical BPM;
- local-analysis unavailability without presenting it as whole-command failure.

`--write` never expands collection. If adding `--write` changes the candidate/source selected or causes Librosa/CAA provider work that the same prepared target would not otherwise perform, the implementation violates this design.

---

## 15. Verification requirements

Artwork tests must prove observable outcomes, not only mocked method calls:

- exact Release approved main-front selection;
- Release Group fallback only after definitive exact absence/no eligible approved front;
- transient exact failure does not trigger Release Group fallback;
- native size fallback and non-JPEG-original behavior;
- preserve existing sidecar/embedded art by default;
- local `cover.jpg` can become authoritative embed source when no embedded art exists;
- partial embedded-art album is preserved as a whole by default;
- `replace_existing: true` produces one uniform cover across sidecars/tracks;
- multidisc reuses identical bytes and writes each required `cover.jpg`;
- verified `Album.artpath` update;
- invalid/oversized payload cannot replace existing state;
- embedding is followed by real media-file reopen verification on supported fixture formats.

BPM tests must prove:

- base install path does not import Librosa at plugin startup;
- `[audio]` extra exposes the supported Librosa dependency;
- existing BPM avoids analysis by default;
- `recalculate_existing: true` forces analysis only when local analysis is enabled;
- decimal preservation and optional rounding;
- full and centered-window analysis behavior;
- octave normalization only by ×2/÷2 and only when enabled;
- missing backend/decoder/analyzer failure stays local;
- importer/library parity;
- `--apply` updates DB but not audio tags;
- `--apply --write` synchronizes the exact canonical BPM and real MediaFile reopen confirms it;
- existing DB BPM can sync to the file without Librosa invocation.

Use deterministic tiny/synthetic audio fixtures for normal tests. Live CAA checks, if retained, are opt-in and excluded from the normal test suite.

---

## 16. Public configuration after this phase

The relevant final shape is:

```yaml
fields:
  cover: true
  bpm: true

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
  mood:
    enabled: false
```

`coverartarchive` is the only artwork authority implemented in this phase. There is no BPM provider authority list to configure because local analysis is the only new BPM evidence source.

---

## 17. Implementation boundaries

Keep implementation objective and split by responsibility:

1. Artwork domain/config + CAA metadata selection.
2. Artwork binary application: validation, sidecars, `Album.artpath`, embedding, multidisc.
3. BPM config/domain + optional lazy Librosa analyzer.
4. BPM integration into import/library planning, DB application, and existing file sync.
5. Cross-path preview, docs, packaging, and integrated regression verification.

Artwork and BPM are one product phase and one feature branch, but each boundary should remain independently testable. Do not introduce framework abstractions beyond what these two concrete capabilities need.

## References

- Cover Art Archive API: https://musicbrainz.org/doc/Cover_Art_Archive/API
- MusicBrainz Picard CAA size behavior reference: https://picard-docs.musicbrainz.org/en/latest/config/options_cover_art_archive.html
- Librosa beat tracking API: https://librosa.org/doc/latest/generated/librosa.beat.beat_track.html
- Librosa tempo API: https://librosa.org/doc/latest/generated/librosa.feature.tempo.html
- beets Album API: https://beets.readthedocs.io/en/latest/api/library.html
- beets MediaFile integration is already exercised by the existing Noqlen `file_sync.py` and semantic file-sync tests.
