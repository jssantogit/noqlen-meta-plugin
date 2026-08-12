# Wave 0B Foundation Implementation Contract

## Status and scope

Wave 0B implements only the internal contracts needed by later V3 waves. It
does not enable a V3 feature, add public configuration, add a provider, expand
provider output, add acquisition, or add a file target. Existing V2 behavior
remains the operational behavior.

## Canonical field and entity model

`beetsplug/noqlenmeta/field_contracts.py` is the source of truth for canonical
field IDs and intrinsic field facts. `FieldContract` records only:

- canonical name and compatibility aliases;
- the explicit set of allowed asserted `EntityKind` subjects;
- `Cardinality`;
- `ResolverKind`;
- valid target classes;
- intrinsic V2 legacy/default metadata where needed.

Provider authority, provider-local quality, acquisition, network behavior and
writer functions do not belong to a field contract. Target adapters remain
separate because AlbumInfo, TrackInfo, library models, MediaFile, sidecars and
assets have different lossless representation rules.

The asserted entity vocabulary is Release, Release Group, Medium, Recording,
Work and Artist. `PartialDate` preserves annual, monthly and complete calendar
precision without invented components. It validates real calendar dates and
deliberately has no ordering that would pretend missing precision is known.

`allowed_entities` is the only field-level source of truth for evidence scope.
It is not an inheritance rule: allowing Release and Recording evidence for a
field preserves two distinct assertions and never promotes a Release value to a
Recording. Target classes and target adapters separately describe persistence,
so the field contract does not need an ambiguous singular persistence entity.
The current multi-entity contracts are:

- genres, styles and moods: Recording, Release and Artist;
- media and format descriptions: Release and Medium;
- composer, lyricist and arranger: Work and Recording;
- producer, conductor, performer, featured/guest artist and artist credit:
  Recording and Release;
- alternate/localized titles and transliterations: Recording, Release and
  Work.

Strict concepts retain strict subjects, including Recording for ISRC and
recording date, Work for ISWC, and Release for edition and release status.
Evidence, provider capabilities and authority rules all validate their asserted
subject against the same field contract.

Multiple identifiers use `IdentifierCollection` containing typed
`ExternalIdentifier` values. Canonical `isrcs` and `iswcs` are plural and
lossless. Native scalar `Item.isrc` remains a future compatibility projection:
one canonical ISRC may project safely, while multiple values must not select an
arbitrary first value. Work identity and ISWC are first-class/queryable
concepts but gain no lookup or file tag in this wave.

The registry includes all V2 fields and all required V3 Core concepts. A
registered field without an implemented target or capability remains correctly
unwriteable and unacquired.

## Evidence envelope

`beetsplug/noqlenmeta/evidence.py` defines ordinary metadata evidence separately
from V2 `MetadataCandidate`:

- `SubjectRef` identifies the exact asserted entity with typed known IDs;
- `AcquisitionProvenance` distinguishes exact lookup, structurally validated
  match, searched candidate and supporting-entity traversal;
- `MetadataEvidence` carries canonical field/value, subject, provider,
  acquisition scope, source reference, provenance and optional provider-local
  confidence.

Acquisition scope may differ from asserted entity. For example, a Recording
acquisition can traverse to evidence that asserts a Work. The field contract
prevents evidence from claiming the wrong entity. Provenance and confidence do
not enter the canonical musical value. The identity and AcoustID subsystems do
not use this ordinary evidence envelope.

`MetadataCandidate` remains unchanged for V2 adapters and resolvers. Later
domain waves may adapt ordinary provider output to `MetadataEvidence` as they
start emitting new canonical values.

## Provider capabilities

`ProviderSpec` remains the static adapter identity and its `supported_fields`
surface remains compatible. `ProviderCapability` separately declares one
field, asserted entity, acquisition scope, typed identity prerequisites and
discrete lazy-planning characteristics. Alternative prerequisites mean that any
listed path can initiate the current adapter; they are descriptive and do not
introduce an acquisition planner. Characteristics describe direct lookup,
search, response reuse or supporting traversal; there is no arbitrary cost
score.

Current adapter characteristics are represented as follows:

- MusicBrainz: direct exact canonical-ID lookup, response reuse and supporting
  traversal only where the V2 adapter already traverses;
- Discogs: direct provider release-ID lookup, search fallback and response
  reuse;
- iTunes: direct collection/provider-identity or UPC path, search fallback and
  response reuse;
- Last.fm: direct top-tags request from validated entity context or MBID and
  response reuse, without generic search;
- LRCLIB: exact `/api/get` request from validated track context and response
  reuse, without generic search.

The built-in capabilities are a structured representation of existing V2
adapter output only. Cover Art Archive, AcoustID and local analysis remain
outside the ordinary provider registry. Deezer is not registered. No adapter
emits a new field and no provider call has been added.

## Authority roles and V2 resolution

`beetsplug/noqlenmeta/authority.py` defines Primary, Secondary, Fallback,
Corroboration Only and Ineligible. Rules are keyed by canonical field, asserted
entity, acquisition scope and provider. Unlisted combinations are Ineligible.
Corroboration Only cannot produce a canonical value alone, and Fallback remains
distinct from Secondary.

The active matrix contains only proposal rows backed by current ordinary
provider capabilities. Deferred V3 rows remain non-executable until their
domain wave adds a capability. CAA, identity, AcoustID and local analysis retain
their separate authority domains.

The V2 resolver continues to use its exact ordered authority semantics.
`translate_v2_authority` preserves field/provider ordinal rank without guessing
new V3 roles. Existing `resolution.authority`, `min_confidence` and
`preserve_existing` behavior therefore remains unchanged.

## Registry consistency

Cross-registry tests require:

- provider capabilities to reference registered fields;
- executable authority rules to reference registered capabilities;
- current AlbumInfo and TrackInfo mappings to reference registered fields;
- current flexible DB registrations to reference typed DB contracts;
- every public V2 field to resolve to a registered concept.

Only the names of simple V2 flexible fields are derived from the field registry.
`field_types.py` continues to declare the actual beets types. Mapping and writer
logic is not derived or moved into the registry.

## Structured persistence boundary

Future structured credits, Recording-to-Work relationships, aliases,
provenance/method versions and necessary rejected evidence may persist only as
plugin-owned state in the beets library context. That state:

- is not another library database;
- is rebuildable from canonical beets values and reacquired/recomputed evidence;
- is not audio metadata and creates no private V3 audio tag;
- is not a provider or authority source;
- never replaces canonical values owned by beets;
- is optional when opening an existing V2 library.

Wave 0B has no consumer that needs structured relationship persistence, so it
adds no tables, schema migration, persistence protocol or speculative record
types. The boundary above is the frozen contract for the wave that first has a
real consumer.

## Cache version contract

`EntityCacheKey` identifies provider, entity type, entity ID and parser/schema
version. Existing callers use the compatible default version `v1`. Exact keys,
including version, reuse successful responses and definitive misses for one
command. Different versions do not collide. Transient exceptions remain
uncached. The cache remains command-lifetime only; pacing, retries and provider
transports are unchanged.

## V2 compatibility freeze

- `fields.cover` remains valid and resolves only to Front artwork intent.
- `front_artwork` carries the enabled V2 default behind the `cover` alias.
- `lyrics_languages` remains distinct from `vocal_languages`.
- `year` remains edition year and distinct from current partial `date`, original
  date and recording date.
- `original_date` is the sole canonical original-date ID; `originaldate` is its
  conceptual compatibility alias and does not add public configuration.
- styles, moods and artist-context fields retain their existing DB and legacy
  `NOQLEN_*` read/write behavior.
- the four MusicBrainz IDs and AcoustID configuration remain unchanged and
  isolated.
- V2 ordered authority configuration remains unchanged.
- no existing `NOQLEN_*` tag is removed and no new V3 private tag is added.
- disabled future V3 concepts have no provider capability and cannot cause
  provider calls.

## Compatibility CI

The existing CI compatibility job verifies the declared boundaries without a
MediaFile override:

- `beets==2.12.0`, the minimum supported beets release;
- `beets<3`, which resolves the latest available compatible beets 2.x release.

The main suite remains deterministic and offline. Live provider tests remain
opt-in and do not gate CI.

## Deliberately not implemented

Wave 0B does not implement new MusicBrainz, Discogs, iTunes or LRCLIB fields;
Deezer; credits; Work traversal; ISRC/ISWC lookup; lyrics sidecars; Back/disc
artwork; Key, Energy or Danceability; new CLI flags; new public configuration;
additional provider calls; persistent cache; or structured-state tables. These
remain work for their approved later waves.
