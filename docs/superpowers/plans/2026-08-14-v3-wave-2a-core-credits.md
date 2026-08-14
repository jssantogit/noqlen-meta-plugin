# Noqlen Meta V3 Wave 2A Core Credits Plan

## Goal and boundary

Implement the mandatory V3 structured-credit core:

```text
shared exact provider acquisition -> scoped typed credit evidence
-> specialized credit resolution -> one ChangePlan per Release or Recording
-> preview -> DB/native apply -> optional lossless file projection
```

The fields are `composers`, `lyricists`, `producers`, `arrangers`,
`conductors`, `performers`, `featured_artists`, and
`structured_artist_credits`. Guest relations remain a controlled
`CreditRole.GUEST_ARTIST` represented by `featured_artists`; no second public
guest field is added. Credits preserve canonical party identity, known MBID,
credited-as text, role, asserted scope, instrument, relationship type and type
ID, source entity, provider ordering where meaningful, and evidence provenance.

This wave does not rewrite `artist`, `albumartist`, `title`, or `album`; alter
the four-MBID identity flow; use credits in autotagger scoring; search for a
Recording or Work; promote Release assertions to Recording; or implement any
Wave 2B field. Technical engineers remain deferred unless an already acquired
payload can be preserved by the same private structure without a new public
field.

## Real target audit

The dependency contract remains `beets>=2.12,<3`. Programmatic inspection used
isolated environments for the actual compatibility endpoints available on
2026-08-14:

| Lane | beets | MediaFile | Result |
| --- | --- | --- | --- |
| Minimum | 2.12.0 | 0.17.0 | Audited |
| Latest supported | 2.13.1 | 0.17.0 | Audited |

Both lanes expose the same relevant contracts:

- `Item.composers`, `composers_ids`, `lyricists`, `lyricists_ids`,
  `arrangers`, and `arrangers_ids` are fixed fields using beets delimited-list
  types. The singular historical names are not fixed Item fields.
- MediaFile exposes plural `composers`, `lyricists`, and `arrangers`; it does
  not expose their ID fields.
- Track artist structure has fixed `artists`, `artist_credit`,
  `artists_credit`, `mb_artistid`, and `mb_artistids`. Album artist structure
  has the corresponding album fields. These are parallel projections and do
  not by themselves guarantee aligned, lossless artist-credit nodes.
- Neither beets nor MediaFile has native producer, conductor, performer,
  instrument, or performer/instrument relationship fields.
- Untyped flexible fields persist lists incorrectly; approved name projections
  must use explicit beets types. Complete relationships must not use DSV.
- ID3v2.3 may join multivalues with `/`; MP4 has no lossless performer plus
  instrument representation. A MediaFile self-round-trip does not establish
  ecosystem interoperability.

The resulting native/file policy is:

| Canonical concept | Native DB | MediaFile | Wave 2A write policy |
| --- | --- | --- | --- |
| Composer names | `composers` | plural composers | Write only when the complete accepted name projection round-trips for the concrete format |
| Composer IDs | `composers_ids` | none | DB only |
| Lyricist names | `lyricists` | plural lyricists | Same concrete-format lossless gate |
| Lyricist IDs | `lyricists_ids` | none | DB only |
| Arranger names | `arrangers` | plural arrangers | Same concrete-format lossless gate |
| Arranger IDs | `arrangers_ids` | none | DB only |
| Producer/conductor | none | none | Typed DB name projections only; file BLOCKED |
| Performer/instrument | none | none | Typed DB name projection plus structured state; file BLOCKED, including MP4 |
| Featured/guest | artist fields are not role fields | no safe role target | DB projection/state only; never rewrite primary artist tags |
| Artist-credit nodes | parallel native fields | parallel fields | Capture/state only unless alignment and joins are proven lossless without changing primary strings |

The implementation contract will record the audit commands, concrete field
types, per-format observations, and any narrower write result found by real
fixture tests. No dependency range changes are permitted.

## Architecture decisions

1. Add `credits.py` with immutable `CreditRole`, `CreditParty`,
   `CreditReference`, `ArtistCreditNode`, and `ArtistCredit`. Roles are closed;
   relationship parsers cannot emit arbitrary canonical role strings.
2. `CreditParty.name` is canonical and non-empty. Optional MBID and relationship
   type IDs use canonical UUID validation. Empty credited-as, instrument,
   relation type, join phrase, and source entity text normalize to `None` where
   the contract permits absence. Credited-as never replaces canonical name.
3. `CreditReference.scope` must be one of the role's approved entities.
   Instrument is valid only for `PERFORMER`. Structural deduplication uses MBID
   when known and otherwise the exact canonical party name, plus role, scope,
   instrument, relationship identity, and source entity. Equal display names
   with different MBIDs remain separate.
4. `ArtistCredit` is an ordered tuple of nodes. Each node preserves artist MBID,
   canonical name, credited name, join phrase after that node, and zero-based
   position. Contributor relations are never used to manufacture artist-credit
   joins.
5. Rename the reserved `artist_credits` contract to the final
   `structured_artist_credits` without a public alias because the old name was
   never public or persisted. Keep 0..n structured cardinality and exact scope
   contracts from the task.
6. Extend the closed `CanonicalValue` vocabulary only with typed credit
   collections. `MetadataEvidence` continues to own provider, asserted subject,
   acquisition scope, source identity, and confidence; canonical objects do not
   duplicate provider provenance.
7. Add `credit_resolution.py`. It validates authority by field/entity/scope,
   unions compatible structural units, corroborates identical units, preserves
   distinct instruments and credited-as variants, and emits REVIEW only for the
   materially conflicting unit. Omission never deletes and existing state is
   monotonic: equal/subset means KEEP, safe strict superset means PROPOSE.
8. Keep Release and Recording credit ChangePlans separate. `ChangePlan` remains
   field-keyed, and no Release plan is copied to Items. Work assertions derived
   from an exact Recording are resolved in that Recording's track plan while
   retaining `scope=WORK` inside each relation.
9. Extend `MusicBrainzSemanticClient` profiles to Release and Work as well as
   Recording. Cache coverage includes entity, exact MBID, schema version, and
   include union. One sufficient payload serves every enabled field for that
   entity; narrower cached coverage never satisfies richer needs.
10. Recording credits add only `artist-rels`; existing genres/tags/isrcs/
    work-rels/place-rels needs remain one deterministic union. Work credits add
    only the audited artist relationship include. Release credits add only the
    audited relationship include. Disabled credit fields add no include or call.
11. Parse the beets-normalized `artist_relations` shape. A present relation type
    ID must be a canonical UUID and match the audited mapping; malformed or
    unknown present IDs fail closed. Text fallback is accepted only for audited
    relation names when the ID is absent. One malformed relation is skipped.
12. Work credits come only from Works reached through approved Recording
    `performance` relations. Exact Work payloads are shared with ISWC/language.
    Generic `writer` does not become composer or lyricist.
13. Structured Recording and Release artist credits come directly from their
    MusicBrainz artist-credit arrays. They remain parallel metadata and never
    replace the selected beets display identity.
14. Extend `ReleaseProviderEnrichment` to retain release evidence and safely
    assigned track evidence from one concrete Discogs response. Release
    `extraartists` with blank tracks remains Release scoped. Nonblank `tracks`
    is never global. Track assignment is emitted only through exact selected
    medium/position occurrence mapping; otherwise Recording-level Discogs
    credit emission is deferred, not guessed.
15. The Discogs role parser uses normalized whole roles and explicit token
    boundaries. `Lyrics By`, `Producer`, `Arranged By`, `Conductor`, explicit
    instrument roles, `Featuring`, and `Guest` are eligible. `Written-By` is
    retained as unprojected diagnostic structure and never called composer.
    Release credits are secondary authority and never provider votes.
16. Persist query projections in typed Item/Album fields. Composer, lyricist,
    and arranger use audited native name and ID fields. Producer, conductor,
    performer, and featured artist names use plugin-owned typed multivalue
    fields. Query projections are explicitly non-canonical views of full
    relationships.
17. Persist complete accepted relationships in versioned tables inside the
    current beets library SQLite database. Rows reference an existing Item or
    Album owner and store typed columns for field, role, party identity/name,
    credited-as, instrument, relation identity, source entity, ordering, and
    provenance key. Artist-credit nodes use a focused sibling table. No Item or
    Album data is duplicated, no second database exists, and no JSON/DSV blob is
    used.
18. Structured tables are created lazily on first credit apply, are optional on
    read, and are fully reconstructible. Opening a V2 library requires no
    migration. The schema has an explicit version table/name and rejects unknown
    versions rather than mutating blindly. Wave 2A never destructively deletes
    existing credit rows because a provider omitted them.
19. Structured-state application is part of the same authorized apply outcome
    as query projections. Existing-library writes use the prepared plan and the
    current library transaction boundary where possible. Importer plans queue
    immutable accepted state and attach it after beets persists the selected
    Album/Items; no provider is called in the persistence hook.
20. File sync reuses candidate-copy, snapshot, unrelated-tag verification,
    atomic replacement, and recovery safety. Only audited name projections are
    candidates. Unsupported structure is a file blocker but remains DB-safe
    under `--partial`. No `NOQLEN_*` credit tag is introduced.
21. Public defaults enable all eight final fields. There is no `credits.enabled`
    subtree and no per-role public authority configuration.

## TDD execution

### 1. Canonical credit values and final contracts

Create failing tests in `tests/test_credits.py`, `tests/test_evidence.py`, and
`tests/test_field_contracts.py` for:

- every controlled role and forbidden arbitrary role;
- canonical party names, UUIDs, credited-as normalization, and no name-to-MBID
  invention;
- role/scope validation and performer-only instrument;
- relation type/source entity validation;
- explicit provider ordering and deterministic unordered canonicalization;
- same name/different MBID separation, same MBID/credited-as variants, and
  multiple instruments;
- ordered artist-credit nodes and exact joins for A, A feat. B, A & B,
  credited-as variants, and multiple joins;
- final field names, 0..n cardinality, STRUCTURED resolver, target classes, and
  allowed scopes without aliases.

Implement `credits.py`, update `field_contracts.py` and `evidence.py`, and run:

```text
pytest tests/test_credits.py tests/test_evidence.py tests/test_field_contracts.py
ruff check beetsplug/noqlenmeta/credits.py beetsplug/noqlenmeta/evidence.py beetsplug/noqlenmeta/field_contracts.py
```

Commit the canonical model and contracts.

### 2. Capabilities, authority, and relationship identity audit

Add failing tests in `tests/test_provider_specs.py` and
`tests/test_authority.py` for every implemented field/entity/provider tuple and
for unlisted combinations remaining ineligible. Audit MusicBrainz relationship
type IDs against normalized beets payloads and MusicBrainz relationship
documentation, then freeze only verified IDs and exact fallback names in tests.

Implement MusicBrainz primary and Discogs secondary capabilities at their real
scopes. Do not add Discogs Recording capability until unambiguous occurrence
mapping is implemented and tested. Commit capability and authority policy.

### 3. MusicBrainz Recording and Work credits

Add focused synthetic normalized payload tests in
`tests/test_musicbrainz_semantic.py` for:

- one Recording lookup with the exact include union and zero extra calls;
- disabled credits adding no `artist-rels`;
- producer, Recording arranger, conductor, performer instrument/vocal,
  multiple instruments, featured and guest relationships;
- exact type-ID acceptance, absent-ID audited fallback, malformed/unknown
  present-ID fail-closed behavior, and malformed-row isolation;
- canonical versus credited-as names, direction, ordering, source entity and
  relation identity preservation;
- exact Work composer, lyricist and arranger extraction from the same Work
  response used for ISWC/language;
- generic writer non-promotion and zero Work lookup when Work-credit fields are
  disabled;
- failed artist relationships preserving ISRC/Work/recording-date output and a
  failed Work-credit branch preserving Work ID/ISWC and siblings.

Make Work lookup profile-aware, compute entity include unions, and implement
the narrow parsers. Run the MusicBrainz, cache, Work identity and failure tests,
then commit exact Recording/Work credit acquisition.

### 4. MusicBrainz Release credits and artist-credit structure

Add failing tests in `tests/test_musicbrainz_release_catalog.py` and
`tests/test_musicbrainz_semantic.py` for:

- one exact Release acquisition serving Wave 1, V2, Release credits and artist
  credit;
- conditional Release relationship include coverage;
- release producer/conductor/performer retention at Release scope;
- exact Recording and Release artist-credit node order, IDs, canonical names,
  credited names and joins;
- relationship failure preserving already parsed release catalog evidence.

Generalize Release cache profiles without duplicating `_fetch_release`, and
extend shared release enrichment. Commit Release credits and structured artist
credits.

### 5. Discogs conservative credit parsing and occurrence scope

Add failing tests in `tests/test_discogs_release_catalog.py` and
`tests/test_discogs_provider.py` using the same concrete Release fixture/result:

- one total concrete request for V2, Wave 1 and credits;
- exact accepted role spellings and rejected substring/compound ambiguity;
- `Written-By` non-promotion;
- blank `tracks` retaining Release scope;
- nonblank `tracks` never becoming global;
- structurally matched medium/position track extraartist assignment;
- multidisc occurrence handling and ambiguous scope omission;
- one malformed credit not discarding catalog candidates/evidence.

Implement only mappings proved by these tests. If current selected occurrence
context cannot prove Discogs Recording assignment, omit that capability and
document Release-only Discogs credits rather than add positional zip or title
matching. Commit the conservative parser and response reuse.

### 6. Specialized monotonic credit resolution

Create failing `tests/test_credit_resolution.py` covering all golden union and
existing-state cases:

- primary-only, compatible primary plus secondary, and eligible secondary-only;
- structural corroboration without provider vote;
- same party/role/scope/instrument deduplication;
- separate instruments, roles, scopes, MBIDs, and credited-as variants;
- existing superset KEEP, incoming safe superset PROPOSE, provider subset KEEP,
  and omission/no evidence producing no deletion;
- partial overlap safe union and isolated REVIEW for material role/scope
  disagreement without blocking unrelated credits;
- deterministic output independent of irrelevant provider order;
- provider unavailable and malformed relation absence.

Implement `credit_resolution.py`, compose its decisions with release or track
plans only, and commit the resolver plus ChangePlan integration.

### 7. Query projections and structured library state

Create failing tests in `tests/test_credit_state.py`, `tests/test_field_types.py`,
`tests/test_track_mapping.py`, `tests/test_library_mapping.py`, and application
tests for:

- lazy schema creation in the current library DB and no second database file;
- schema version validation and an untouched V2 library opening normally;
- typed row round trips for every relationship and artist-credit node property;
- owner isolation between Album and Item and no Release-to-Recording promotion;
- monotonic upsert without omission deletion;
- native composer/lyricist/arranger name and ID projections;
- typed producer/conductor/performer/featured name query projections;
- no delimiter-encoded person/instrument canonical value;
- strict/partial apply, stale current-state rejection, and second-run no-op.

Implement a focused `credit_state.py`, typed field registrations, current-state
readers, target mappings, and transactional application hooks. Commit
persistence and query projections.

### 8. Importer and existing-library orchestration

Add failing integration tests in `tests/test_importer_track_planning.py`,
`tests/test_beets_integration.py`, `tests/test_library_cli.py`, and related
application tests for:

- enrichment only after selected `Action.APPLY` and exact selected IDs;
- selected beets composer/lyricist/arranger/artist-credit values included in
  effective current state so no false REVIEW occurs;
- no credit influence on match score or four-MBID identity;
- pending structured state persisted after beets creates Album/Items without
  reacquisition;
- credits-only config executing importer and `beet nm QUERY` workflows;
- `--all` changing scope only;
- release and recording credits appearing in separate previews/plans;
- `--apply`, `--partial`, and second run behavior;
- one MusicBrainz Recording per track, one sufficient Work per Work, one
  Release total, and one Discogs concrete Release total.

Replace hard-coded Wave 1 field gates with implemented capability checks where
that reduces duplication without changing V2 behavior. Commit importer and
existing-library integration.

### 9. Lossless file projections

Add cross-format tests in `tests/test_file_sync.py` and MediaFile audit tests for:

- composer, lyricist and arranger names only on concrete formats that preserve
  the complete accepted list;
- role IDs remaining DB-only;
- producer, conductor, performer/instrument, featured/guest and structured
  artist-credit file blockers;
- explicit MP4 performer blocker;
- unsupported file target coexisting with DB-safe partial apply;
- no primary artist/albumartist/title/album changes;
- no private credit tags;
- zero provider calls during write and unchanged snapshot/atomic/recovery
  invariants.

Implement only targets demonstrated lossless by the tests. Commit file policy.

### 10. Public configuration and documentation

Add failing public-doc/config tests, then:

- enable the eight final `fields` defaults;
- create `docs/specs/033-v3-core-credits/implementation-contract.md` with the
  canonical structures, accepted relationship IDs/types, scopes, authority,
  acquisition profiles/counts, Discogs role/scope mapping, persistence schema,
  query projections, real native/file matrix, importer/library behavior,
  failure isolation, and explicit deferrals;
- update README, configuration, field/provider, workflow, and compatibility
  pages already checked by `check_public_docs`;
- state that V3 is upcoming, keep package version unchanged, and avoid Wave 2B
  claims.

Run public documentation tests and commit documentation.

## Commit sequence

1. Wave 2A implementation plan and target audit.
2. Canonical credit values and final field contracts.
3. Provider capabilities, authority, and audited relationship identities.
4. MusicBrainz Recording/Work credit acquisition.
5. MusicBrainz Release and structured artist-credit acquisition.
6. Discogs conservative scoped credit parser.
7. Specialized monotonic credit resolution and planning.
8. Structured library state and query projections.
9. Importer and existing-library orchestration.
10. Audited lossless file projections.
11. Public configuration and implementation/user documentation.
12. Focused regression corrections discovered by final verification.

Every commit follows red/green focused tests and stages named files only. Do not
amend, merge, tag, release, publish, change package version, add private credit
tags, or begin Wave 2B.

## Final verification

Run focused suites throughout and finish with:

```text
pytest
ruff check .
python scripts/check_public_docs.py
python scripts/check_repo_contamination.py
mkdocs build --strict
git diff --check
```

Inspect GitHub workflows to confirm Python 3.10-3.14, beets 2.12.0, latest
beets `<3`, package, documentation, and audio-analysis jobs remain configured.
Review the final diff and repository searches for inferred role by name,
Release-to-Recording promotion, primary artist/title rewrites, Work/Recording
search, AcoustID credit evidence, credit scoring, duplicate entity acquisition,
JSON/DSV relationship state, new `NOQLEN_*` tags, display-name-only merging,
unsafe Discogs assignment, Wave 2B leakage, unfinished placeholders, secrets,
private paths, and user-library data.
