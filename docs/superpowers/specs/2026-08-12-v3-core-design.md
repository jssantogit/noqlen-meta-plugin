# Noqlen Meta V3 Core Design

**Status:** Approved design
**Date:** 2026-08-12
**Target release:** 3.0.0

## 1. Purpose

Noqlen Meta V3 is the release intended to close the essential feature surface of Noqlen Meta. After 3.0.0, the project should primarily evolve through quality improvements, documentation, additional providers, specialized metadata, and optional features rather than by filling basic metadata gaps.

Noqlen Meta remains the definitive metadata companion for beets. It does not become a library manager.

V3 prioritizes metadata that materially improves real libraries, filtering, discovery, smart-playlist inputs, identity, and interoperability. It does not pursue exhaustive tag-count parity with other projects.

## 2. Product boundary

### In scope

- Descriptive and catalog metadata.
- Semantic metadata.
- MusicBrainz identity and AcoustID identity evidence.
- Recording and work identifiers.
- Lyrics, including synchronized lyrics.
- Artwork assets.
- Useful locally-derived and provider-derived audio features.
- Structured credits and artist participation metadata.
- Safe beets database and file application.
- Existing-library enrichment and importer-safe enrichment.

### Out of scope for the V3 core

- File and folder organization.
- General-purpose import/copy/move workflows.
- Playlist management.
- Ratings.
- Navidrome management.
- Duplicate-management workflows.
- A separate library database.
- Job-management infrastructure for its own sake.
- ReplayGain, which remains better served by the existing beets ecosystem.
- Dynamic popularity/ranking as canonical music metadata.
- A subjective "vibe engine".

## 3. Metadata philosophy

V3 uses a hybrid target policy:

1. Prefer native beets/MediaFile fields whenever they correctly represent the musical concept.
2. Use Noqlen-specific typed fields only when the concept has a stable and interoperable representation.
3. Prefer interoperable sidecars or associated assets when embedding would lose information or create format-specific private metadata.
4. Keep provenance, confidence, rejected evidence, and diagnostic state internal.

A new persistent Noqlen field is justified only when it represents a stable musical concept that remains useful outside Noqlen Meta.

V3 is "complete where it matters in practice," not exhaustive for every possible catalog tag.

## 4. Architectural model

V3 keeps and generalizes the V2 safety pipeline:

**Evidence -> Canonical Resolution -> ChangePlan -> Preview/REVIEW/BLOCKED -> Apply -> Write**

A provider never writes directly to beets or to an audio file.

Providers only produce normalized evidence. Resolvers choose canonical values. Planners decide whether the selected value has a safe target. Application executes an already validated plan.

Identity, AcoustID, ordinary metadata, artwork/assets, audio analysis, and file writing remain distinct authority domains even though they share the same planning and safety model.

### 4.1 Domain boundaries

V3 is organized into seven domains:

1. **Identity and identifiers**
   - MusicBrainz release, release-group, recording, and release-track identity.
   - AcoustID identity evidence.
   - ISRC.
   - ISWC.
   - Work and Recording identity.
   - Explicit repair flows for identity-critical artist fields.

2. **Catalog and release metadata**
   - Current edition date/year.
   - Original release date/year.
   - Recording date.
   - Release type.
   - Secondary release types.
   - Release status.
   - Edition.
   - Label, catalog number, barcode, country, media, and format metadata.

3. **Semantic and language metadata**
   - Genres.
   - Styles.
   - Moods.
   - Vocal languages.
   - Instrumental state.
   - Alternate/localized titles.
   - Script and transliteration.
   - Track version/mix.

4. **Credits**
   - Composer.
   - Lyricist.
   - Producer.
   - Arranger.
   - Conductor.
   - Performers and instruments.
   - Featured and guest artists.
   - Structured artist credits.
   - Low-cost technical credits where reliable.
   - Low-cost classical metadata where it naturally follows from the same relationships.

5. **Lyrics**
   - Plain lyrics.
   - Synced lyrics.
   - Lossless `.lrc` sidecars.

6. **Artwork**
   - Front cover.
   - Back cover.
   - Disc art when its implementation and acquisition remain low-cost and reliable.

7. **Audio features**
   - BPM.
   - Key.
   - Energy.
   - Danceability.
   - Deterministic derived buckets for filtering.

## 5. Field model and interoperability

### 5.1 Target classes

Every field belongs to one of four target classes:

- **Native beets/MediaFile**: preferred whenever semantically correct.
- **Interoperable non-native tag**: used only when there is a stable cross-tool representation and a defensible per-format mapping.
- **Interoperable sidecar/asset**: used where the richer representation should not be degraded to fit an embedded tag.
- **Internal-only state**: provenance, confidence, diagnostics, rejected evidence, and resolution metadata.

### 5.2 Scope and cardinality

Scope and cardinality are part of the field contract. Providers do not emit untyped key/value strings.

Examples:

- ISRC: Recording/track, zero-to-many.
- ISWC: Work, zero-to-many.
- Edition: Release, optional single canonical value.
- Composer: Work or Recording credit, zero-to-many.
- Producer: Recording or Release credit, preserving the source scope.
- Vocal languages: Recording, zero-to-many.
- Release type: canonical single value.
- Secondary release types: set.
- Recording date: Recording.
- Explicitness: Recording/track, tri-state.

Values must not be promoted or inherited across scopes without explicit evidence.

### 5.3 Multi-value preservation

When the concept is multi-valued, V3 remains lossless internally. A restricted file target may receive a simplified representation, but the canonical state must not destroy valid values.

This applies especially to ISRCs, ISWCs, credits, languages, secondary release types, alternate titles, genres, and styles.

### 5.4 Unknown is not false

Fields where lack of evidence is not a negative assertion use explicit unknown state.

Examples:

- `explicit / clean / unknown`
- `instrumental = true / false / unknown`

Partial date precision is preserved. A source that knows only a year must not be converted to January 1 of that year.

### 5.5 Derived metadata

Derived buckets such as `energy_level`, `danceability_level`, and `tempo_range` are deterministic functions of canonical numeric values. They are not provider evidence and do not participate in resolving the underlying value.

## 6. Identity and identifiers

V3 preserves the V2 identity boundary rather than blending identity into general metadata enrichment.

### 6.1 MusicBrainz identity

The existing four-field identity flow remains conceptually separate from ordinary enrichment:

- release MBID;
- release-group MBID;
- recording MBID;
- release-track MBID.

Identity-critical repair remains explicit and conservative.

### 6.2 AcoustID

AcoustID remains an identity-evidence subsystem, not a generic metadata provider.

It must not:

- write MusicBrainz IDs directly;
- rescue a structurally weak or ambiguous candidate by adding positive score;
- use release data from AcoustID as a substitute for MusicBrainz release assignment;
- mutate audio files as part of standalone AcoustID application.

Generated fingerprints continue to require explicit authority.

### 6.3 ISRC

ISRC is first-class V3 metadata because it identifies a recording. V3 should retrieve and preserve valid ISRCs when recording identity is sufficiently established.

ISRC must never be guessed from artist/title similarity alone.

### 6.4 ISWC and Work

ISWC is a first-class but optional Work identifier. Coverage is not required for a track to be considered successfully enriched.

Work identity supports composer/lyricist relationships, classical metadata, and the distinction between a musical composition and its recordings.

## 7. Dates, release classification, and edition

V3 keeps three distinct date concepts:

- `date/year`: the specific edition represented by the library item.
- `originaldate/original_year`: the first publication of the relevant commercial release lineage.
- `recording_date`: when the specific recording was made, when reliable evidence exists.

One date must not be inferred from another.

Release classification is split into distinct concepts:

- `release_type`: Album, EP, Single, and equivalent primary types.
- `release_secondary_types`: Live, Compilation, Soundtrack, Remix, and equivalent secondary classifications.
- `release_status`: Official, Promotion, Bootleg, Pseudo-release, and equivalent status.
- `edition`: edition-specific designation such as Deluxe Edition, Anniversary Edition, or Limited Edition.

Edition is release-scoped and uses a conservative normalization policy. Format, remaster state, release type, and country are not silently collapsed into edition.

Materially incompatible edition evidence results in REVIEW rather than concatenation or arbitrary selection.

## 8. Structured credits and artist participation

A credit is modeled as a relationship rather than as an unstructured string. The conceptual record contains:

- person or artist;
- role;
- scope;
- optional instrument;
- related musical entity.

The mandatory credit surface includes:

- composer;
- lyricist;
- producer;
- arranger;
- conductor;
- performers and instruments;
- featured and guest artists.

Technical roles such as mixing, mastering, and recording engineer are included only when reliable data is available at low marginal acquisition and implementation cost.

### 8.1 Artist names remain beets-owned by default

V3 enriches artist-credit structure without automatically rewriting `artist` or `albumartist` in ordinary enrichment.

The plugin may preserve:

- primary artists;
- featured artists;
- guest artists;
- credited display names;
- MusicBrainz artist IDs.

Corrections to primary `artist`/`albumartist` remain an explicit identity-sensitive operation with preview and review gates.

### 8.2 Scope preservation

A release-level producer is not automatically copied to every recording. A recording performer is not automatically promoted to an album-level performer.

Scope may be displayed contextually, but persistence preserves the relationship that the source actually asserted.

## 9. Multilingual titles and recording versions

Alternate-title metadata preserves, where available:

- text;
- language;
- script;
- title type, such as original, official translation, transliteration/romanization, or alias.

The main `title` and `album` chosen by beets are not automatically replaced during ordinary enrichment.

Track version/mix is represented separately from the main title. Examples include:

- Radio Edit;
- Extended Mix;
- Remaster;
- Acoustic;
- Live;
- Demo;
- Instrumental.

Where possible, V3 preserves both a normalized version type and the source's more specific description. It does not infer version semantics solely from title keywords when no reliable evidence exists.

## 10. Language and explicitness

V3 introduces a canonical recording-level language model that distinguishes:

- vocal language(s);
- artist language metadata;
- lyric language evidence;
- instrumental state.

`vocal_languages` combines reliable recording/lyrics evidence without promoting artist language into sung language.

Instrumental state is tri-state: true, false, or unknown.

Explicitness is also tri-state:

- explicit;
- clean;
- unknown.

Absence of an explicit flag never implies clean. Track-level explicitness is authoritative for the recording; an album-level value may be derived as a summary but must not make every track explicit simply because one track is explicit.

## 11. Lyrics V3

Lyrics are modeled as related representations:

- plain lyrics;
- synchronized lyrics;
- `.lrc` as the preferred lossless synchronized sidecar target.

V3 must not degrade synchronized lyrics merely to fit a weaker target. It may write plain lyrics to an embedded field while preserving the synchronized form in `.lrc`.

Matching should use identity when available and then appropriate title/artist/album/duration/version evidence.

Existing content is handled conservatively:

- identical content produces no change;
- a clearly superior candidate can be proposed;
- materially different plausible lyrics produce REVIEW;
- an existing `.lrc` is not overwritten merely because a new candidate exists.

Local sidecars may be inspected before network acquisition when that avoids unnecessary calls.

## 12. Artwork V3

Artwork has an explicit type.

### Required for 3.0.0

- front cover;
- back cover.

### Conditional for 3.0.0

- disc art, including per-disc assets for multidisc releases, when acquisition and persistence remain low-cost and reliable.

### Deferred by default

- booklet;
- spine;
- arbitrary artwork galleries.

CAA remains the primary artwork authority for an established MusicBrainz release identity. iTunes, Deezer, or other providers may act as safe fallbacks after provider audit.

Artwork never contributes positive identity evidence.

Candidate selection may consider correct artwork type, resolution, dimensions, availability of a sufficiently high-quality original, and rejection of unsuitable thumbnails. V3 does not need visual similarity or aesthetic ranking.

Associated assets are preferred where universal embedding is not reliable. Expected naming includes `cover.jpg`, `back.jpg`, and, when supported, `disc.jpg` or per-disc equivalents.

## 13. Audio Features V3

V3 supports:

- BPM;
- Key;
- Energy;
- Danceability.

The canonical model stores the musical value while retaining origin, method, confidence, and methodology version internally.

### 13.1 Hybrid acquisition

Audio features may come from:

- trusted provider evidence;
- local analysis;
- an already valid existing value.

Provider values do not automatically defeat local analysis, and local analysis does not automatically defeat a trusted provider. The field resolver applies field-specific authority and confidence.

The plugin must remain useful offline.

### 13.2 BPM

BPM resolution should account for normal measurement tolerance and common half/double-tempo relationships rather than treating every numeric mismatch as an independent conflict.

### 13.3 Key

Key is normalized internally to an unambiguous canonical musical representation. Enharmonic equivalents should not become artificial conflicts.

Low-confidence local key analysis must not be silently written.

### 13.4 Energy and danceability

Energy and danceability must be useful enough for filtering and smart-playlist inputs. V3 must not copy simplistic formulas merely to expose fields.

Local energy analysis should draw on defensible acoustic evidence such as intensity, dynamics, spectral properties, and rhythmic activity.

Danceability should derive from defensible rhythmic characteristics such as beat regularity, temporal stability, and other relevant groove/rhythm features, rather than being a trivial function of BPM and energy.

The normalized scale contract must be documented and methodology-versioned so algorithm changes do not silently redefine historical values.

### 13.5 Derived buckets

V3 exposes deterministic filtering helpers such as:

- `energy_level`;
- `danceability_level`;
- `tempo_range`.

Bucket thresholds are specified by the implementation design and documentation, are recalculable from canonical raw values, and never participate in resolving those values.

### 13.6 Local-analysis cost

Local analysis is lazy and incremental. Existing valid results are reused. File changes or incompatible methodology changes invalidate the relevant result.

BPM, Key, Energy, and Danceability should share decode and reusable acoustic feature extraction where practical rather than decoding the same file four independent times.

## 14. Classical metadata

V3 supports classical metadata opportunistically where it follows naturally from relationships already being acquired.

Useful low-cost fields include:

- work;
- movement;
- movement number and total;
- composer;
- conductor;
- orchestra/ensemble;
- performers and instruments.

V3 does not require a complete classical-specific tagging subsystem with deep Work hierarchies and specialized naming rules. Such specialization may follow in a later 3.x release.

## 15. Provider authority and resolution

Provider authority is field-specific and scope-specific. There is no universal ordering where one provider is "better" for every field.

### 15.1 Identity gate

Release- or recording-specific enrichment cannot gain authority over an entity whose identity is not sufficiently established.

A strong-looking Deezer, Discogs, iTunes, artwork, or lyrics result cannot repair an ambiguous MusicBrainz identity merely by agreement.

### 15.2 Evidence model

Provider evidence includes at least:

- field/concept;
- value;
- entity/scope;
- provider;
- match quality or acquisition provenance required by that field.

The resolver works on evidence rather than provider return values directly.

### 15.3 No universal confidence score

V3 does not expose a universal 0-100 confidence score across unrelated domains.

Domain-specific quantitative scoring may exist internally where meaningful. User-visible state uses semantic outcomes:

- ACCEPTED;
- REVIEW;
- BLOCKED.

Diagnostics may additionally use high/medium/low confidence with an explanation tied to the relevant evidence.

### 15.4 Conflict policy by field kind

- Exclusive fields require a compatible canonical winner; material unresolved disagreement becomes REVIEW.
- Multi-value fields may union compatible values after normalization, deduplication, and scope validation.
- Taxonomic fields keep their specialized semantic resolver.
- Derived fields are recalculated and have no provider conflict of their own.

Corroboration improves confidence but never acts as a naive vote. Two weak sources do not automatically defeat a structurally more authoritative source.

### 15.5 Provider failure is not deletion

Timeout, rate limit, malformed response, missing result, or temporary provider failure means absence of new evidence. It never means that an existing value should be deleted.

### 15.6 Formal authority matrix

V3 maintains an explicit field-by-provider matrix with roles such as:

- primary authority;
- secondary authority;
- fallback;
- corroboration only;
- not eligible.

The matrix is a testable project artifact and is the basis for adding or rejecting new providers.

## 16. Provider strategy

V3 first improves the existing provider set and only then adds providers that close real, high-value gaps.

Each current provider is audited for:

- field coverage;
- matching quality;
- field-specific authority;
- normalization quality;
- retry, timeout, pacing, and response-bound behavior;
- caching;
- offline testability.

### 16.1 MusicBrainz

Primary structural source for identity and relationships. The V3 audit should evaluate fuller use of:

- ISRC;
- ISWC and Works;
- composer/lyricist/producer/performer relationships;
- recording dates;
- release status/type/secondary types;
- artist credits;
- aliases, scripts, and transliterations;
- technical credits when they are available without disproportionate cost.

MusicBrainz is not promoted to universal authority for artwork, lyrics, or all edition-specific facts.

### 16.2 Discogs

Primary or strong authority candidate for release-specific physical/catalog facts such as:

- labels;
- catalog numbers;
- barcodes;
- country;
- formats/media;
- edition details;
- credits;
- genre/style evidence.

Free-text and semi-structured values require careful normalization.

### 16.3 Last.fm

Remains focused on semantic tags used as genre/style/mood evidence through the Noqlen taxonomy and noise classifier. It does not gain identity or catalog authority merely because it exposes similar strings.

### 16.4 iTunes

Remains a lightweight fallback candidate for fields such as genre, date, explicitness, artwork, and selected digital metadata after audit. It is not an identity authority.

### 16.5 LRCLIB

Feeds the complete V3 lyrics pipeline rather than a plain value assignment. Provider abstraction should allow additional lyrics sources later without redesigning resolution.

### 16.6 Cover Art Archive

Remains the primary artwork authority for a known MusicBrainz release, expanded to the supported artwork types.

### 16.7 AcoustID

Remains isolated from the generic provider stack as identity evidence.

### 16.8 New providers

A new provider enters V3 only when it closes a material high-value gap that existing providers cannot sufficiently resolve.

Evaluation considers:

- missing field/value;
- coverage;
- quality;
- operational cost;
- API stability;
- matching requirements;
- concrete gain over existing providers.

Deezer is the leading candidate for audit, especially for explicitness, digital track metadata, dates, and artwork fallback. Its exact role is decided field-by-field after evidence rather than assumed in advance.

Spotify, Beatport, and other providers are not added for name recognition or provider-count parity.

## 17. Acquisition strategy and cost control

More providers must not imply that every provider is called for every track.

Acquisition is layered:

1. use established identity and already available evidence;
2. query the necessary structural/authoritative provider;
3. resolve the field;
4. invoke fallback providers only for unresolved high-value gaps.

If a field is already resolved with sufficient authority, further provider calls are avoided unless the resolver explicitly needs corroboration.

The planner may maintain an internal acquisition-cost model that distinguishes existing evidence, cheap calls, justified fallbacks, and expensive calls that should only occur for still-missing requested fields.

## 18. Preview, apply, and write

The V3 CLI remains conceptually simple despite the larger feature set.

### 18.1 Preview by default

`beet nm QUERY` remains non-mutating and is the primary explanation surface.

Preview groups results by domain and prioritizes changes, conflicts, and blocked operations instead of dumping every unchanged field.

### 18.2 Apply

`--apply` applies approved metadata to the beets database and may materialize explicitly supported associated assets/sidecars such as artwork and `.lrc`, subject to the same verified-plan rules.

It does not rewrite embedded audio tags by default.

### 18.3 Write

`--apply --write` synchronizes supported approved values to embedded file metadata.

Write must not:

- perform a second provider lookup;
- rerun resolution;
- rerun audio analysis;
- silently change the plan between preview and mutation.

The planned current state and target state act as preconditions. A stale target is not overwritten.

### 18.4 Safety states

- ACCEPTED: enough evidence and a safe target exist.
- REVIEW: a legitimate unresolved choice remains.
- BLOCKED: the requested operation is unsupported or unsafe.

REVIEW is not an error, and provider failure does not automatically create REVIEW when it simply means there is no new proposal.

### 18.5 Partial application

Safety is tracked at the appropriate unit rather than forcing every field in an album into one indivisible status.

With `--partial`, accepted units may apply while REVIEW/BLOCKED units remain untouched. `--partial` never means force or "ignore safety".

### 18.6 Sensitive operations remain explicit

The following remain outside ordinary enrichment side effects:

- MusicBrainz identity repair;
- primary artist/albumartist correction;
- fingerprint generation when missing;
- other identity-critical textual mutation.

### 18.7 Domain selection

V3 may expose simple domain-level selection such as lyrics, artwork, audio, or credits, or an equivalent interface compatible with the current CLI.

It should not create one CLI flag per metadata field. Field configuration remains configuration-level; the CLI selects the kind of work requested for an execution.

### 18.8 Whole-library execution

`--all` changes query scope, not authority.

Whole-library runs should use cache and acquisition budgeting, tolerate isolated provider failures where safe, and produce a concise aggregate summary while retaining detailed diagnostics on demand.

## 19. Importer behavior

beets remains the owner of importer matching and library management.

Noqlen Meta enriches after the importer has established the selected identity and only when the importer action authorizes application.

Noqlen Meta does not place its provider stack or AcoustID evidence into competition with the beets autotagger for initial release selection.

## 20. Provenance and diagnostics

Provenance and confidence are decision metadata, not music metadata.

They remain internal to Noqlen state/database structures where persistence is required and are exposed through preview, REVIEW, and diagnostics.

Audio-analysis method/version is also preserved internally so later algorithm changes can distinguish values produced under incompatible methodologies.

These details are not written as ordinary tags into music files.

## 21. Testing and quality strategy

### 21.1 Unit tests

Cover:

- normalization;
- scope/cardinality;
- resolvers;
- authority matrix;
- tri-state behavior;
- partial dates;
- credit deduplication;
- key normalization;
- half/double BPM handling;
- bucket derivation;
- deterministic conflict behavior.

### 21.2 Provider contract tests

Use sanitized offline fixtures for:

- complete responses;
- missing fields;
- malformed payloads;
- timeouts/rate-limit behavior at adapter boundaries;
- ambiguous matches;
- schema variants.

The primary test suite must not depend on live provider availability.

### 21.3 Integration tests

Use temporary beets libraries and representative real media formats where applicable to exercise:

- preview -> apply -> write;
- database persistence;
- sidecars;
- artwork assets;
- stale-state detection;
- importer hooks;
- identity/AcoustID isolation;
- format-specific write mapping.

### 21.4 Golden scenarios

V3 release candidates should pass representative end-to-end cases including:

- ordinary album;
- reissue/remaster;
- multidisc release;
- compilation;
- single/EP;
- featured artist;
- multiple ISRCs;
- synchronized lyrics;
- conflicting edition evidence;
- multilingual/transliterated release;
- live recording;
- artwork fallback;
- target modified between plan and write;
- provider failure;
- AcoustID incompatibility with structural assignment;
- insufficient identity.

### 21.5 Safety invariants

Tests should make the following regressions release-blocking:

- preview mutates DB or audio;
- `--apply` rewrites embedded audio tags;
- write performs new provider acquisition;
- a provider writes directly to a target;
- AcoustID writes MusicBrainz IDs;
- artwork improves identity score;
- provider absence deletes an existing value;
- existing identity becomes positive evidence for repairing itself;
- REVIEW applies silently;
- stale targets are overwritten;
- `--all` increases authority;
- `--partial` acts as force.

### 21.6 Property-based testing

Use where the combinatorial space justifies it, especially for:

- date precision/normalization;
- multi-value cardinality and deduplication;
- structured credits;
- key normalization;
- BPM half/double relationships;
- deterministic resolution independent of irrelevant provider ordering.

## 22. Performance

Performance is evaluated across separate budgets:

- network calls;
- CPU analysis;
- filesystem I/O;
- memory.

The objective is predictable scaling rather than maximum benchmark speed.

### 22.1 Shared local audio analysis

BPM, Key, Energy, and Danceability should share decoding and reusable feature extraction where practical.

### 22.2 Versioned cache

Cache keys include the dimensions that change result meaning, such as provider/entity identity and relevant normalizer or analysis methodology versions.

Invalidation should be targeted rather than flushing unrelated cached evidence.

## 23. V2 compatibility and migration

V3 is evolutionary rather than a reset.

V2 configuration remains valid whenever the same semantics remain safe. When change is necessary, prefer:

1. compatible aliases;
2. in-memory migration with a clear warning;
3. explicit rejection only when preserving old behavior would be semantically dangerous.

Existing V2 data is reused:

- BPM;
- genres/styles/moods;
- MusicBrainz IDs;
- AcoustID state;
- lyrics;
- artwork;
- other supported persisted values.

New V3 fields begin as absent rather than requiring library reconstruction.

A field whose methodology changes substantially must preserve enough internal method/version information to know whether an old value can be reused or should eventually be recomputed.

## 24. File-format compatibility

Every writable field requires an explicit target mapping for the supported MediaFile/audio backends, such as FLAC/Vorbis, MP3/ID3, MP4/M4A, Opus, and any other format that the project claims to support.

If a field lacks a stable lossless representation for a format, the planner must report the limitation rather than inventing private tags solely to claim support.

## 25. Implementation waves

V3 is one release built and stabilized in waves.

### Wave 0 — audit and foundation

- Full current-provider audit.
- Field/provider authority matrix.
- beets/MediaFile target audit.
- V3 schema, scope, cardinality, and internal provenance model.
- V2 migration design.
- Objective decision on Deezer and any additional provider.

No large new feature should precede this foundation.

### Wave 1 — catalog, dates, and identifiers

- original date/year;
- recording date;
- ISRC;
- ISWC/Work;
- release type;
- secondary types;
- release status;
- edition;
- refinement of existing catalog/media fields.

### Wave 2 — credits and structured musical metadata

- core credits;
- structured artist participation;
- multilingual titles/script/transliteration;
- track version/mix;
- vocal languages;
- instrumental state;
- explicitness;
- low-cost technical/classical metadata where justified.

### Wave 3 — Lyrics V3

- plain and synchronized lyrics;
- `.lrc` sidecars;
- matching/conflicts/existing-content policy;
- preview/apply/write integration.

### Wave 4 — Artwork V3

- front and back artwork;
- safe fallbacks;
- quality/resolution handling;
- verified assets;
- disc art when still low-cost and reliable.

### Wave 5 — Audio Features V3

- revised BPM;
- Key;
- Energy;
- Danceability;
- hybrid local/provider resolution;
- shared analysis;
- methodology versioning;
- objective buckets.

### Wave 6 — provider ecosystem closure

- implement only additional providers justified by Wave 0;
- tune cache, fallback, pacing, and lazy acquisition.

### Wave 7 — 3.0.0 hardening

- golden scenarios;
- cross-format integration;
- whole-library runs;
- importer checks;
- stale-state verification;
- real V2 migration tests;
- performance checks;
- public documentation;
- CLI/config validation;
- release-candidate hardening.

No discretionary new feature work is added in Wave 7.

## 26. 3.0.0 release blockers

The following are mandatory for the V3 core:

- mature identity/identifier behavior;
- current/original/recording date semantics;
- release type, secondary types, status, and edition;
- ISRC and supported ISWC/Work enrichment;
- essential structured credits;
- structured artist participation without automatic artist-name takeover;
- vocal language, instrumental state, and explicitness;
- multilingual titles/script/transliteration;
- track version/mix;
- plain and synchronized lyrics with lossless `.lrc` support;
- front and back artwork with safe fallback strategy;
- BPM, Key, Energy, Danceability, and objective derived buckets;
- complete audit of existing providers;
- field-specific authority/conflict model;
- V2 compatibility/migration;
- preserved preview/apply/write safety invariants.

## 27. Conditional V3 features

These are attempted in their natural implementation wave but do not block 3.0.0 if their cost or complexity becomes disproportionate:

- disc art;
- deeper mixing/mastering/recording engineering credits;
- advanced classical metadata and deep Work hierarchies.

They may land in a later 3.x release without implying that the V3 core was incomplete.

## 28. Definition of done for each wave

A wave is complete only when its relevant scope has:

- implementation complete;
- unit tests;
- provider contracts where applicable;
- relevant integration tests;
- minimum technical documentation;
- migration behavior defined;
- no regression in safety invariants;
- acceptable performance;
- coherent preview/apply/write behavior.

## 29. Definition of V3 completeness

The goal of 3.0.0 is that future work feels like refinement, broader coverage, specialized support, or optional capability.

After V3, adding another provider, improving energy analysis, supporting booklets, expanding classical tagging, or adding another lyrics source is evolution.

Discovering that the project still lacks fundamental recording identifiers, core credits, synchronized lyrics, original-release context, key/audio features, or safe edition/conflict policy would mean V3 failed its purpose.

The final rule remains:

> **Quality, real-world utility, interoperability, and safety are more important than feature count.**
