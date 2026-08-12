# Noqlen Meta v2 Enrichment Design

Status: approved architecture design for the next major product initiative.

This document records the user-approved v2 direction. It is intentionally compact: it defines durable product boundaries and implementation sequencing without recreating the staged process overhead retired by the Playbook V2.2 retrofit.

## Objective

Noqlen Meta v2 expands ordinary enrichment from a mostly release-centric metadata workflow into one reusable enrichment system for releases, tracks, artists, artwork, and optional local audio analysis.

The product should remain useful as a single beets plugin installation. Safe zero-credential capabilities work by default; credentialed providers and heavier local analysis extend coverage without becoming mandatory dependencies.

The v2 design must preserve the existing strengths of the project:

- provider-independent normalized candidates;
- explicit authority and confidence resolution;
- preview before mutation;
- database-first application;
- explicit authorization for media-file writes;
- deterministic offline tests with opt-in live integration evidence;
- MusicBrainz identity and AcoustID evidence remaining separate from ordinary enrichment.

## Non-goals

- Do not create one mini-architecture per new field.
- Do not require fetchart, embedart, autobpm, or another beets plugin for v2 features.
- Do not make a heavyweight ML stack part of the base installation.
- Do not treat country, language, release country, artist origin, or legal nationality as interchangeable concepts.
- Do not silently flatten multivalued metadata into one arbitrary scalar value.
- Do not make identity scoring depend on ordinary enrichment.
- Do not make `--write` trigger extra provider work or analysis that was absent from the prepared plan.

## 1. Architecture

The existing release and track enrichment boundaries become the basis for a scope-oriented architecture:

```text
Noqlen Meta v2 enrichment
├── Release enrichment
│   ├── genres
│   ├── styles[]
│   ├── existing release metadata
│   └── artwork
├── Track enrichment
│   ├── bpm
│   ├── moods[]
│   ├── lyrics_languages[]
│   └── other track metadata
├── Artist enrichment
│   ├── artist_countries[]
│   ├── artist_areas[]
│   └── artist_languages[]
├── Local analysis
│   ├── bpm
│   └── mood analysis (optional, not required for the first v2 cut)
└── File synchronization
    └── authorized by --write
```

Providers and analyzers produce normalized observations/candidates. Resolution remains provider-independent. Only a resolved change plan can reach database, artwork, or media-file application.

```text
provider / analyzer
       ↓
normalized evidence
       ↓
resolver
       ↓
change plan
   ├── beets database
   ├── artwork sidecar
   └── media-file tags/artwork
```

No provider writes directly to the database or audio files.

### Artist scope

`ArtistEnrichmentContext` is a distinct domain value rather than extra fields stuffed into `TrackEnrichmentContext`. At minimum it carries artist name plus available external identifiers and enough credit context to preserve multiple credited artists deterministically.

beets has no independent artist entity that Noqlen Meta should mutate as a new subsystem. Artist-scope evidence is therefore resolved into the selected album/item targets that reference those artists. Multiple credited artists are preserved in stable credit order with duplicate values removed.

## 2. Canonical fields and semantics

The canonical v2 values are:

```text
styles             -> tuple[str, ...]
moods              -> tuple[str, ...]
lyrics_languages   -> tuple[str, ...]
artist_languages   -> tuple[str, ...]
artist_countries   -> tuple[str, ...]
artist_areas       -> tuple[str, ...]
bpm                -> float
```

`styles` and `moods` are genuinely multivalued. v2 removes the current effective singular-style limitation rather than selecting the first style merely because an existing target is scalar.

`bpm` resolves to one finite numeric value. Multiple tempo observations are evidence for one final BPM, not a list to persist.

Semantic distinctions are explicit:

- `country` remains release/edition country.
- `artist_countries` means geographic artist origin/identification, not legal citizenship.
- `artist_areas` retains the more precise area/city/region evidence when available.
- `lyrics_languages` means languages associated with the song/work lyrics.
- `artist_languages` means languages musically associated with the artist through directly identified works/tracks; it must never be presented as the artist's personal spoken-language profile.

Artist area may be retained in the database even when the default user-facing/tag output exposes only country.

### Lossless database representation

The canonical in-memory representation remains tuples for multivalued text. The plugin must declare appropriate beets flexible-field types for new fields so database round trips preserve type and order. If beets does not offer a suitable built-in multivalue type for a target, Noqlen Meta should provide a small typed codec rather than join values into an ambiguous scalar string.

No mapping layer may silently reduce a tuple to its first value. A destination that cannot represent a value losslessly produces an explicit mapping blocker in preview.

## 3. Provider strategy

Providers are assigned by semantic responsibility rather than by a desire for every provider to fill every field.

### MusicBrainz

MusicBrainz is the primary zero-credential semantic backbone for v2 where its data model fits:

- existing MusicBrainz identifiers remain preferred lookup anchors;
- recording-to-work relationships support `lyrics_languages` from Work lyric-language data;
- Artist area data supports `artist_areas` and derived `artist_countries`;
- community tags may contribute controlled semantic evidence such as moods/styles, but raw tags are not persisted directly as moods.

MusicBrainz ordinary enrichment remains separate from MusicBrainz identity repair.

### Cover Art Archive

Cover Art Archive is the first artwork authority when a MusicBrainz release identifier is available. Noqlen Meta resolves and downloads artwork itself; it does not require the beets `fetchart` plugin.

### Discogs

Discogs remains the primary built-in authority for release `styles`. Existing release metadata behavior is preserved. Credential requirements keep Discogs opt-in by default.

### Last.fm

Last.fm may contribute moods and styles through normalized tag evidence when configured. Because it requires credentials, it remains opt-in.

### Mood normalization

Raw provider tags do not become `moods` directly. They pass through a versioned, controlled normalization layer that maps accepted synonyms to canonical mood labels and ignores unrelated tags. Provider confidence/weight must survive normalization so ordinary resolution policy can still decide whether the evidence is eligible.

The first v2 cut does not require local ML mood classification. The local-analysis boundary is designed so a future optional backend can contribute mood evidence without changing the resolver or persistence architecture.

### BPM evidence

The approved Artwork + Audio design is authoritative for initial-v2 BPM sourcing. There is no external BPM provider in the first v2 release. Librosa is the only local BPM backend, and local BPM analysis is optional and disabled by default.

`TempoObservation` keeps the resolution and persistence boundary open to future evidence sources, but no provider observation or multi-source conflict policy is implemented for this release.

## 4. Artwork pipeline

Artwork uses a dedicated value and pipeline instead of forcing image bytes or URLs into normal `MetadataValue`.

Conceptually:

```text
ArtworkCandidate
├── provider
├── source_id
├── source_url
├── kind
├── confidence
├── mime_type?
├── width?
├── height?
└── release identity
```

Artwork application has distinct stages:

1. resolve the selected artwork candidate;
2. download through a bounded network boundary;
3. validate response size, image type, and basic integrity before mutation;
4. prepare the sidecar destination and embedding plan;
5. save the album artwork sidecar under `--apply`;
6. embed the selected artwork into eligible audio files only under `--apply --write`.

The normal default sidecar behavior is compatible with a `cover.jpg`-style album artwork file, while keeping the exact filename/configuration explicit and deterministic.

Invalid or oversized artwork is rejected before it can replace an existing sidecar or be embedded.

## 5. Application and CLI authority

v2 remains database-first and reuses `--write` as the single general authorization for modifying audio files.

```text
beet nm ...
→ preview only

beet nm --apply ...
→ apply approved database changes
→ save approved external artwork sidecar when applicable

beet nm --apply --write ...
→ all --apply behavior
→ synchronize supported metadata tags to audio files
→ embed approved artwork
```

`--write` requires apply intent; it is not an independent enrichment mode.

`--write` authorizes only file mutations already represented in the prepared plan. It does not enable fields, call additional providers, calculate fingerprints, run local BPM analysis, or otherwise expand collection work by itself.

### Generic file synchronization

The special identity-tag implementation remains a useful safety precedent, but ordinary v2 metadata gets a reusable file-sync layer:

```text
FileSyncPlan
├── metadata tag changes
├── artwork changes
├── target snapshots
└── validation results

        ↓ --write

FileSyncApplication
```

Format-specific adapters map canonical fields to tag representations. Native multivalue representation is used when the container/tag format supports it. Unsupported lossless mappings are surfaced as blockers; the plugin must not silently join or discard values.

The preview clearly separates database, sidecar-artwork, and audio-file effects before any mutation starts.

## 6. Import and existing-library parity

The same enrichment core must work in both paths:

- importer-selected releases/tracks;
- already-imported library albums/items.

The paths may have different selection and application adapters, but they share contexts, normalized candidates, resolution, semantic rules, and field mapping policy. A v2 field is not considered complete if it only works during import while an equivalent existing-library target is technically available, or vice versa.

## 7. Configuration and defaults

v2 is useful without API credentials. Providers that are safe and usable without credentials are enabled by default; credentialed integrations remain opt-in.

The target default shape is:

```yaml
fields:
  genres: true
  styles: true
  moods: true
  bpm: true
  lyrics_languages: true
  artist_countries: true
  artist_areas: false
  artist_languages: true
  cover: true

providers:
  musicbrainz:
    enabled: true
  coverartarchive:
    enabled: true
  discogs:
    enabled: false
  lastfm:
    enabled: false

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

The existing generic `resolution.authority`, `resolution.min_confidence`, and `resolution.preserve_existing` model remains the preferred control surface. New features do not each get their own bespoke resolution system.

An illustrative authority direction is:

```yaml
resolution:
  authority:
    styles: [discogs, lastfm, musicbrainz]
    moods: [lastfm, musicbrainz, local]
    lyrics_languages: [musicbrainz]
    artist_countries: [musicbrainz]
```

Provider lists are filtered by actually implemented capability. A provider named in a default authority list must not be contacted unless the provider is enabled and supports that field.

## 8. Lightweight local audio analysis

The base runtime remains light. Local BPM analysis is an optional dependency set of the same Noqlen Meta package:

```text
pip install beets-noqlenmeta
→ base plugin and zero-credential enrichment

pip install "beets-noqlenmeta[audio]"
→ same plugin plus local audio-analysis backend
```

This is not a dependency on another beets plugin.

The base package must not import a heavyweight audio-analysis stack at startup. The analysis backend is lazy and isolated behind a small boundary such as:

```text
TempoAnalyzer.analyze(path)
        ↓
TempoObservation
├── bpm
├── confidence
└── backend
```

If local BPM analysis is enabled but Librosa is unavailable, that capability reports unavailable and ordinary enrichment continues. There is no external BPM provider in this implementation. If no BPM evidence exists, the preview reports that BPM could not be enriched; the command does not fail solely because the optional audio extra is absent.

Librosa is the initial optional backend and remains isolated behind `TempoAnalyzer`; the core architecture does not expose Librosa-specific objects or APIs.

## 9. Failure behavior

External and optional capabilities fail locally whenever safe:

- Cover Art Archive unavailable: artwork is unavailable; unrelated metadata continues.
- MusicBrainz Work has no usable lyric language: leave `lyrics_languages` without fabricated evidence.
- one track's BPM analysis fails: report that track; continue other targets where safe.
- optional audio backend missing: mark local analysis unavailable; do not crash ordinary enrichment.
- invalid artwork payload: reject it before any sidecar or embed mutation.
- provider returns conflicting highest-authority values: use the existing review behavior rather than arbitrary selection.

Structural failures remain blocking, including stale target snapshots before file mutation, inconsistent plans, or a mapping that cannot preserve required semantics.

Application results must make partial outcomes explicit. No failure may leave an unreported impression that all requested targets were updated successfully.

## 10. Verification strategy

Tests are organized around durable boundaries, not fake parallel implementations.

- domain and resolver behavior: pure deterministic tests;
- Release / Track / Artist contexts: validation and normalized-candidate tests;
- external providers: sanitized representative fixtures where they add regression value;
- network failure handling: narrow boundary stubs/mocks;
- mood normalization: deterministic taxonomy mapping tests;
- artwork: small valid/invalid payloads, size/type validation, safe temporary destinations;
- BPM: short synthetic or purpose-built audio fixtures with known tempo characteristics;
- database mappings: round-trip tests proving multivalued fields remain lossless;
- file sync: temporary media files, followed by reading the resulting tags/artwork to verify the observable outcome;
- import and existing-library parity: shared behavioral scenarios where possible;
- live external checks: opt-in only and excluded from the normal test run.

No automated test uses a real user music library.

## 11. Migration from 1.0

v2 is a major release because the public enrichment model changes materially from mostly release-level/database-only ordinary enrichment to release + track + artist + artwork + optional analysis with generalized file synchronization and new zero-config defaults.

The migration preserves existing identity and AcoustID contracts unless a separately reviewed change is required.

Notable v2 changes include:

- `styles` becomes losslessly multivalued;
- track enrichment generalizes beyond lyrics;
- artist enrichment becomes a first-class provider scope;
- `--write` becomes general audio-file mutation authority;
- artwork becomes an owned Noqlen Meta capability;
- safe zero-credential providers are enabled by default;
- local audio analysis is available through the package's optional `[audio]` extra.

Existing scalar `style` data must be read as one legacy style value during migration so it can participate safely in preserve/replace decisions. Migration must not delete an existing style merely because the new canonical field is plural.

## 12. Implementation decomposition

The architecture is implemented as three coherent product changes rather than one branch per field or a return to mandatory stage documents.

### A. V2 Foundation

- add Artist scope and normalized artist evidence;
- generalize track enrichment beyond lyrics;
- introduce lossless multivalue database targets;
- establish canonical new fields and migration handling for legacy `style`;
- create generic file-sync planning/application behind `--write`;
- add v2 configuration structure/defaults without provider-specific feature duplication.

### B. Semantic Enrichment

- implement multivalued `styles` end to end;
- add controlled `moods` normalization and provider evidence;
- add `lyrics_languages` from semantically correct work/recording relationships;
- add artist country/area enrichment;
- derive `artist_languages` only from identified musical-language evidence, with semantics documented clearly;
- provide import and existing-library parity.

### C. Artwork + Audio

- add Cover Art Archive artwork candidates and selection;
- bounded artwork download, validation, sidecar application, and embedding under `--write`;
- add the optional `[audio]` Librosa BPM backend, disabled by default;
- preserve the `TempoObservation` boundary for future sources without implementing an external BPM provider;
- verify actual database, file-tag, and embedded-art outcomes.

After these changes, perform one integrated release-readiness pass. Local ML mood analysis is explicitly outside the critical path of the first v2 release; its boundary exists so it can be added later without redesigning the core.

## 13. Success criteria

The v2 architecture is successful when:

1. a base installation can enrich useful metadata with safe zero-credential sources without another beets plugin;
2. releases, tracks, and artist-derived metadata use one resolver/change-plan philosophy;
3. styles and moods remain multivalued without silent data loss;
4. optional BPM analysis uses the lazy local Librosa backend, disabled by default, with no external BPM provider in the first v2 release;
5. artwork can be selected, downloaded, validated, saved, and optionally embedded by Noqlen Meta itself;
6. `--apply` remains database-first while `--write` is the explicit general authority for audio-file mutation;
7. import and existing-library workflows provide equivalent enrichment semantics;
8. optional heavy capabilities do not make the base plugin heavy;
9. identity and AcoustID remain isolated from ordinary enrichment semantics;
10. verification observes the resulting database/tags/artwork rather than relying only on internal success claims.

## Technical references checked during design

- beets supports plugin-declared `item_types` and `album_types` for typed flexible fields: https://beets.readthedocs.io/en/stable/dev/plugins/other/fields.html
- beets' AutoBPM implementation uses Librosa behind its optional `autobpm` installation extra: https://beets.readthedocs.io/en/latest/plugins/autobpm.html
- beets' FetchArt and EmbedArt capabilities are separate plugins; v2 intentionally owns equivalent Noqlen workflows rather than requiring them: https://beets.readthedocs.io/en/latest/plugins/fetchart.html and https://beets.readthedocs.io/en/v2.11.0/plugins/embedart.html
