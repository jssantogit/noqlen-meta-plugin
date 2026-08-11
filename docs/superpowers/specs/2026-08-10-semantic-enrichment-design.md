# Noqlen Meta v2 Semantic Enrichment Design

Status: user-approved design for v2 Semantic Enrichment.

This spec defines the second v2 product change after V2 Foundation + Genre Foundation. It intentionally stays focused on semantic metadata. Artwork/covers and BPM/audio analysis remain in the following Artwork + Audio phase.

## Objective

Make the v2 Foundation produce useful semantic metadata from real provider evidence while preserving the existing Noqlen principles:

- MusicBrainz is the zero-credential semantic backbone;
- Discogs remains the structured style authority when configured;
- Last.fm remains an opt-in community-evidence extension;
- provider output is normalized before resolution;
- no provider writes directly to the database or media files;
- missing evidence is preferable to fabricated metadata;
- importer and existing-library workflows share the same semantics;
- identity and AcoustID remain separate from ordinary enrichment.

This phase covers:

- `genres`;
- `styles`;
- `moods`;
- `lyrics_languages`;
- `artist_languages`;
- `artist_countries`;
- `artist_areas`.

## Non-goals

This phase does not implement:

- Cover Art Archive collection, artwork download, sidecars, or embedding;
- provider/local BPM collection;
- the optional `[audio]` extra;
- local ML mood analysis;
- fuzzy MusicBrainz identity search;
- whole-career artist language crawling;
- persistent API caches or arbitrary request-budget configuration;
- a release/version bump.

## 1. Architecture

Use the Foundation scopes and change-plan pipeline rather than introducing one subsystem per field.

```text
MusicBrainz
├── Release semantic evidence
├── Recording / Track semantic evidence
│   └── Work relationships -> lyrics languages
└── Artist semantic + geographic evidence

Discogs [opt-in]
└── Release -> structured styles + genre evidence

Last.fm [opt-in]
├── Track community tags
├── Release community tags
└── Artist community tags

            ↓
semantic normalization / classification
            ↓
field-specific evidence resolution
            ↓
existing ChangePlan
            ↓
DB -> optional --write file synchronization
```

The existing `ProviderScope.RELEASE`, `TRACK`, and `ARTIST` boundaries remain the public provider organization. MusicBrainz may use related entities such as Work or Area internally, but those are supporting lookups, not new mutation scopes.

## 2. Semantic classification

Community tags are never persisted directly merely because a provider returned them.

All community tags pass through one deterministic bundled classifier:

```text
raw tag
  -> normalization
  -> alias resolution
  -> semantic classification
  -> canonical term
```

Every canonical community-tag term has exactly one primary semantic category:

- `GENRE`;
- `STYLE`;
- `MOOD`;
- `ORIGIN`;
- `DESCRIPTOR`;
- `NOISE`.

A term classified as `MOOD` does not simultaneously become a genre/style merely because the source is ambiguous. This prevents one weak community tag from being copied into multiple fields.

The existing bundled Genre Foundation remains authoritative for genre recognition. The semantic layer extends that idea with:

- a controlled style vocabulary for community-tag classification;
- a hybrid mood taxonomy;
- origin recognition used only for classification/routing, not for fabricating artist origin;
- descriptor/noise filters.

Structurally typed provider data is different from community tags. In particular, Discogs `styles` remain structured style evidence and do not need to pass through the community-tag style allowlist to be preserved as styles.

## 3. Genres

Continue using the existing specialized `GenreEvidence` and genre resolver.

MusicBrainz contributes genre evidence from exact identified entities where available:

- Recording -> Track scope;
- selected Release / related release semantics -> Release scope;
- credited Artist -> Artist scope.

MusicBrainz community tags that classify as `GENRE` may also become weaker community genre evidence.

Discogs structured genres remain release evidence. A Discogs structured style may continue to be promoted to genre evidence when `genres.promote_styles` is enabled and the bundled genre taxonomy recognizes the term.

Last.fm community tags classified as `GENRE` provide optional evidence at Track, Release, then Artist scope.

The existing approved genre ranking remains unchanged in principle:

1. semantic validity;
2. eligibility / minimum quality;
3. scope relevance (`Track > Release > Artist` after quality filtering);
4. distinct-provider corroboration;
5. evidence kind/strength;
6. specificity;
7. provider-native weight as a late tie-breaker;
8. stable deterministic ordering.

Weak Track evidence must not beat strong Release evidence merely because it is Track scope.

`genres.num_genres` remains the configured output count. No parent genre is added just to fill the requested count.

## 4. Styles

Discogs is the structured primary source for `styles` when enabled.

Rules:

- preserve the ordered, deduplicated structured Discogs style tuple;
- continue genre promotion independently when a Discogs style is also a recognized genre;
- MusicBrainz and Last.fm community tags may supply `STYLE` evidence only when the semantic classifier recognizes the term;
- community style evidence primarily expands coverage when structured Discogs styles are absent; it must not turn a strong Discogs tuple into an uncontrolled merged tag soup;
- existing preserve/replace authority behavior remains applicable.

`styles` remains canonically multivalued and lossless in the database. No new style-count knob is introduced in this phase.

## 5. Moods

Moods use a hybrid controlled taxonomy.

The taxonomy contains:

- a canonical core of useful mood labels;
- aliases/synonyms that collapse spelling and closely equivalent terms;
- an explicit allowlist of useful specific moods beyond the core;
- no automatic acceptance of unknown tags.

Examples conceptually:

```text
sad / sadness / melancholic / melancholy -> Melancholic
dreamy -> Dreamy
atmospheric -> Atmospheric    # only if the canonical classifier assigns it to MOOD
seen live -> NOISE
```

MusicBrainz tags provide the zero-config mood source. Last.fm tags may strengthen consensus or extend coverage when configured.

Consensus is valuable but not mandatory. Strong eligible MusicBrainz evidence may resolve a mood without Last.fm; otherwise zero-config moods would be effectively disabled.

Configuration:

```yaml
moods:
  max_moods: 1
```

`max_moods` defaults to `1`. The field remains multivalued internally and supports a bounded configurable range (target: 1..10), but the resolver never fills additional values artificially.

Mood ranking is deterministic and conservative:

1. recognized canonical mood;
2. evidence passes provider/scope quality rules;
3. more relevant scope;
4. distinct-provider corroboration;
5. evidence strength;
6. provider-native weight;
7. stable tie-break.

A small pure mood/semantic resolver should be preferred over extending the generic atomic tuple resolver with field-specific hidden behavior.

## 6. Lyrics languages

`lyrics_languages` is derived from exact MusicBrainz Recording -> Work relationships.

Flow:

```text
Recording MBID
  -> Work relationship(s)
  -> Work lyric language(s)
  -> canonical language codes
```

Persist canonical ISO-style three-letter language codes used by MusicBrainz semantics, for example:

```text
eng
kor
jpn
```

Do not persist translated display names as canonical values.

Rules:

- multiple valid Work languages are ordered deterministically and deduplicated;
- multiple Works may contribute a union of valid languages;
- missing language data means no change;
- explicit no-lyrics/instrumental metadata does not fabricate a language value;
- legacy generic "multiple languages" markers do not replace actual specific languages;
- uncertainty is not inferred from artist country, release country, title script, or other heuristics.

Display layers may show human-readable language names without changing the persisted canonical code.

## 7. Artist languages

`artist_languages` is contextual, not a whole-career profile and not a claim about languages personally spoken by an artist.

It is derived only from the identified Works belonging to the tracks in the current enrichment target.

```text
current target tracks
  -> identified Works
  -> resolved lyrics_languages
  -> ordered/deduplicated union
  -> artist_languages
```

Do not crawl the artist's full MusicBrainz discography or work catalogue.

For multiple credited artists, preserve stable credit order for artist processing and deduplicate final language values. The stored aggregate field represents languages musically associated with the credited artists in the current target context; it is not a per-artist language mapping.

The canonical representation is the same three-letter language-code representation used by `lyrics_languages`.

## 8. Artist areas and countries

MusicBrainz Artist main area is the primary geographic evidence because it represents the area with which the artist is primarily identified.

Persist:

- `artist_areas`: the most specific trustworthy main-area name available for each credited artist;
- `artist_countries`: the trustworthy country derived from that area using MusicBrainz structural geographic information.

Rules:

- process credited artists in stable credit order;
- deduplicate repeated areas/countries without reordering first occurrence;
- use MusicBrainz area type, ISO information, and/or structural ancestry where available;
- an Area supporting lookup may be performed when needed to establish country and is cached like other supporting entities;
- never infer country from artist name, language, release country, title script, or geographic-name string matching;
- `begin-area` is not equivalent to main area and must not override a populated main area;
- a controlled `begin-area` fallback is allowed only when main area is absent and the implementation can preserve the documented "origin/identification" semantics;
- if country cannot be established reliably, keep the specific area if trustworthy and leave `artist_countries` unchanged.

The field describes geographic origin/identification, not legal citizenship.

## 9. Provider collection by scope

### MusicBrainz

MusicBrainz is enabled by default and remains identity-anchored: semantic enrichment uses exact MBIDs already selected/stored by beets/Noqlen rather than fuzzy searches to guess identity.

For each entity, compute the union of includes/capabilities required by the enabled fields before the first lookup. Reuse one payload for every compatible field.

Conceptually:

```text
Release lookup
  -> existing release metadata
  -> genres/tags needed by enabled semantic fields
  -> linked IDs needed by target processing

Recording lookup
  -> genres/tags
  -> artist credits
  -> Work relationships

Work lookup, only when needed
  -> lyric languages

Artist lookup
  -> genres/tags
  -> main area and supporting geographic IDs
```

If relationship payloads already contain sufficient supporting data, reuse them. Perform an additional exact lookup only when the enabled field requires data that is not present.

### Discogs

Discogs remains opt-in due to credentials.

Its current release adapter continues to provide structured `genres` and `styles`; Semantic Enrichment consumes those values through the new semantic resolution flow without changing Discogs into an artist/track crawler.

### Last.fm

Last.fm remains opt-in because it requires an API key.

Expand community-tag collection to the approved lazy fallback order:

```text
Track
  -> if requested semantic fields still lack sufficient eligible evidence
Release
  -> if still unresolved
Artist
```

Fallback is field-aware. If genre is already resolved but mood is not, later scope collection may continue for mood without pretending genre needs more evidence.

Use provider-supported MBIDs when available. Where Last.fm requires textual identity, use the exact existing context rather than introducing a fuzzy identity-search subsystem. Last.fm community evidence remains weaker than exact structured provider data.

## 10. Request efficiency and execution cache

Do not introduce a persistent cache or arbitrary `max_api_requests` configuration in this phase.

Use a command-lifetime in-memory cache keyed conceptually by:

```text
(provider, entity_type, canonical_id)
```

The enabled-field set is known before collection, so the first entity lookup should request the union of needed capabilities. Cache entries therefore represent the planned complete payload for that entity in the current command.

Rules:

- valid responses are reused;
- definitive not-found results may be negatively cached for the command;
- transient/network failures are not converted into permanent "not found" state;
- Work and Artist lookups are deduplicated by exact MBID;
- supporting Area lookups are deduplicated by exact MBID;
- cache lifetime ends with the command;
- `--write` never changes collection, provider calls, or analysis.

Fields disabled in configuration must not trigger provider work required only for those fields.

The optimization model is therefore:

```text
unioned lookup payloads
+ exact-entity deduplication
+ command-lifetime cache
+ lazy fallback
```

rather than an arbitrary request counter.

## 11. Resolution and fallback policy

There is no universal provider authority for every semantic field.

Fallback expands coverage but never lowers eligibility requirements.

Conceptually:

```text
Track eligible evidence?
  yes -> resolve
  no  -> Release eligible evidence?
           yes -> resolve
           no  -> Artist eligible evidence?
```

Each fallback level still passes through the same semantic classifier and quality gates.

For language and geographic fields, absence is preferred to inference.

When eligible evidence conflicts:

- resolve automatically when the field-specific deterministic policy has a safe winner;
- otherwise expose the conflict rather than choosing arbitrarily;
- keep existing `resolution.preserve_existing` behavior;
- keep provider failure separate from evidence conflict.

## 12. Configuration

Keep `fields.*` as the feature on/off switches.

Add only the semantic knobs that have a clear product need:

```yaml
moods:
  max_moods: 1
```

Existing:

```yaml
genres:
  num_genres: 1
  promote_styles: true
```

Provider defaults remain:

```yaml
providers:
  musicbrainz:
    enabled: true
  discogs:
    enabled: false
  lastfm:
    enabled: false
```

Do not add provider calls merely because a field appears in an authority list. Providers are contacted only when enabled and capable of contributing to an enabled field.

## 13. Preview and outcome reporting

The normal preview should show resolved decisions and useful provenance, not dump every raw tag.

Conceptual output:

```text
Track: Example Artist - Example Song

mood
  Melancholic
  source: MusicBrainz
  classified from: melancholy

lyrics_languages
  kor
  source: MusicBrainz Work

artist_languages
  kor
  derived from identified Works in current target
```

Fallback provenance may be shown when useful, for example `source: MusicBrainz release; track evidence insufficient`.

Detailed raw evidence belongs in verbose/debug output.

Outcome states must remain semantically distinct:

- `no-evidence`: provider/entity exists but no eligible value is available;
- `unavailable`: required provider lookup failed or capability is unavailable;
- `conflict`: eligible evidence exists but resolution has no safe winner;
- `blocked`: application cannot preserve required semantics or a structural safety precondition failed.

These states must not all collapse into "unchanged".

## 14. Failure behavior

Provider/network failures are local whenever continuing is safe.

Examples:

- one Work lookup fails -> that track lacks that Work-derived language evidence; unrelated fields continue;
- Last.fm fails -> MusicBrainz/Discogs evidence continues;
- one Artist has no reliable country -> other artists/fields continue;
- unknown community tag -> classify as unknown/noise and do not persist it.

Global/blocking failures remain appropriate for structural problems such as:

- invalid configuration;
- internally inconsistent change plans;
- stale file targets before mutation;
- a destination mapping that cannot preserve canonical semantics;
- corruption/uncertainty in the application boundary that already requires the Foundation's blocking/recovery behavior.

Partial outcomes must remain truthful.

## 15. Import and existing-library parity

A semantic field is not considered complete if it only works during import or only works on existing-library commands when equivalent targets are available.

Both paths share:

- enrichment contexts;
- exact external identifiers;
- provider adapters;
- semantic classification;
- evidence models;
- resolution;
- canonical field semantics;
- mapping policy.

Only selection and final target adapters may differ where beets requires it.

Importer and `beet nm` paths should reuse already-known provider data/IDs when available rather than re-identifying entities.

## 16. Verification strategy

Prefer pure deterministic tests for semantic logic and narrow fixtures/mocks at external boundaries.

Required coverage includes:

### Classification

- aliases and normalization;
- unique category assignment;
- genre/style/mood/origin/descriptor/noise routing;
- unknown tags never persisted automatically;
- representative K-pop, metal, electronic and mood cases.

### Genres

- MusicBrainz Track/Release/Artist evidence;
- weak Track evidence filtered before scope preference;
- distinct-provider corroboration;
- Discogs style promotion preserved;
- current `num_genres` behavior unchanged.

### Styles

- structured Discogs tuple remains ordered/lossless;
- community `STYLE` fallback works when Discogs is absent;
- ambiguous/unknown community tags do not enter `styles`;
- Discogs style can remain a style while independently contributing promoted genre evidence.

### Moods

- synonym collapse;
- specific approved mood acceptance;
- `max_moods=1` default;
- configurable larger limit without artificial filling;
- MusicBrainz-only zero-config decision;
- Last.fm corroboration;
- unresolved conflict reporting.

### Languages

- Recording -> Work -> language code;
- multiple Works/languages ordered and deduplicated;
- missing language -> no fabrication;
- no-lyrics/instrumental -> no language value;
- `artist_languages` derives only from Works in the current target;
- no whole-career traversal.

### Artist geography

- main area preferred;
- country derived only through structural evidence;
- begin-area fallback only when allowed;
- multiple credited artists preserve stable credit order;
- inability to derive country does not discard a trustworthy specific area.

### Collection efficiency

- one lookup per unique planned MusicBrainz entity under normal execution;
- repeated Work/Artist/Area MBIDs reuse cache;
- negative cache only for definitive misses;
- transient errors are not cached as missing;
- Last.fm fallback stops when all requested semantic fields are sufficiently resolved;
- disabled fields do not cause unnecessary lookups;
- `--write` causes no extra provider work.

### End-to-end

- import and existing-library semantic parity;
- database round-trip of new multivalues;
- `--apply` persists expected DB values;
- `--apply --write` reads the resulting real temporary media file back and verifies supported file tags;
- provider failure isolation and truthful partial reporting;
- identity/AcoustID behavior remains unchanged.

No automated test touches a real user music library. Live provider checks remain opt-in and outside the normal deterministic suite.

## 17. Success criteria

Semantic Enrichment is complete when:

1. a credential-free installation can obtain useful `genres`, `moods`, lyrics-language, and artist geographic/language evidence from MusicBrainz when the identified entities contain it;
2. the existing Genre Foundation receives real Track/Release/Artist MusicBrainz evidence without bypassing its resolver;
3. Discogs remains the structured style authority when enabled and its genre-promotion behavior still works;
4. Last.fm can expand/corroborate semantic evidence through lazy Track -> Release -> Artist fallback when configured;
5. `moods` defaults to one canonical mood while remaining losslessly multivalued;
6. `lyrics_languages` and `artist_languages` persist canonical language codes and never infer language from geography;
7. `artist_languages` uses only Works from the current target rather than crawling an artist's career;
8. artist area/country values are structurally derived and never guessed from strings or other unrelated metadata;
9. collection is deduplicated/cached per execution and disabled fields do not create needless requests;
10. missing, unavailable, conflict, and blocked outcomes are distinguishable;
11. importer and existing-library behavior share equivalent semantic rules;
12. database/file outcomes are verified observably where the Foundation provides a writable mapping;
13. artwork/covers and BPM/audio remain cleanly deferred to the next v2 phase.

## Technical constraints confirmed during design

- MusicBrainz API lookups support combined `inc=` subqueries, `tags`, `genres`, and relationship includes such as `work-rels`.
- MusicBrainz Work stores lyric languages and supports multiple languages; explicit no-lyrics is semantically distinct from an actual language.
- MusicBrainz Artist main area is the area with which the artist is primarily identified.
- MusicBrainz Area entities provide area types and ISO codes and participate in structural geographic relationships.
- Last.fm provides community top-tag APIs at track, album, and artist levels and requires an API key for these calls, so it remains opt-in.
