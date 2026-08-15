# V3 Wave 2A Core Credits Implementation Contract

## Status and boundary

Wave 2A implements structured composer, lyricist, producer, arranger,
conductor, performer/instrument, featured/guest, and artist-credit enrichment.
It preserves the V3 pipeline:

```text
exact provider evidence -> specialized credit resolution -> ChangePlan
-> preview -> database/native projection -> optional verified write
```

Credits never participate in beets matching, four-MBID scoring, or AcoustID.
Ordinary enrichment never rewrites `artist`, `albumartist`, `title`, or `album`.
Release relations are not inherited by Recordings.

## Canonical model

`CreditRole` is closed to Composer, Lyricist, Producer, Arranger, Conductor,
Performer, Featured Artist, and Guest Artist. Parsers cannot create arbitrary
canonical roles.

`CreditParty` preserves a nonempty canonical name, optional canonical artist
MBID, optional credited-as name, and all corroborating credited-as variants.
Names never invent MBIDs and credited-as never replaces the canonical name.

`CreditReference` preserves party, role, asserted `EntityKind`, optional
instrument, relationship type and UUID, source entity ID, relation attributes,
direction, and provider ordering key. Instruments are valid only for Performer.
Composer, Lyricist, and Arranger permit Work/Recording scope. Producer,
Conductor, Performer, Featured Artist, and Guest Artist permit
Recording/Release scope.

Structural identity uses party MBID when known and otherwise the exact
canonical name, together with role, scope, instrument, and related source
entity. Equal names with different MBIDs remain separate. Equal MBIDs merge
credited-as variants without becoming an identity conflict. Distinct
instruments remain distinct relations.

`ArtistCredit` is separate from contributor relations. It contains contiguous,
ordered `ArtistCreditNode` values with artist MBID, canonical name, credited
name, exact join phrase, and position. Recording and Release artist credits are
preserved without primary display-name takeover.

## Field contracts and authority

All public fields are 0..n, STRUCTURED, and enabled by default:

| Field | Allowed assertion | MusicBrainz | Discogs |
| --- | --- | --- | --- |
| `composers` | Work, Recording | Primary for implemented Work relations | No executable capability |
| `lyricists` | Work, Recording | Primary for implemented Work relations | No executable capability |
| `arrangers` | Work, Recording | Primary | No executable capability |
| `producers` | Recording, Release | Primary | Secondary for Release |
| `conductors` | Recording, Release | Primary | Secondary for Release |
| `performers` | Recording, Release | Primary | Secondary for Release |
| `featured_artists` | Recording, Release | Primary for explicit guest relation attributes | Secondary for explicit Release Featuring/Guest |
| `structured_artist_credits` | Recording, Release | Primary | Ineligible |

Unlisted combinations are ineligible. There is no provider vote. The field
contracts permit future Recording composer/lyricist evidence, but no executable
MusicBrainz authority is declared because the audited artist-Recording
vocabulary has no equivalent explicit relationship.

## MusicBrainz acquisition

All lookups require exact selected MBIDs and use the existing
`MusicBrainzSemanticClient` coverage-aware command cache. There is no search.

- Recording needs are unioned into one profile. Core relationship fields add
  `artist-rels`; Work-credit fields also require the existing `work-rels` path.
- Each Work reached through an approved Recording `performance` relation uses
  one profile-aware exact Work payload for ISWC, language, and artist relations.
- Release credits and artist credit reuse the exact Release acquisition.
  Contributor relations add `artist-rels`; artist-credit structure itself uses
  the baseline artist-credit payload.
- Disabled credit fields add no relationship include or supporting lookup.
- A present malformed or unknown relationship UUID fails closed. Audited text
  fallback is accepted only when the type ID is absent. One malformed relation
  does not discard sibling or Wave 1 evidence.

Accepted Work relationship identities:

| Type | UUID | Canonical role |
| --- | --- | --- |
| composer | `d59d99ea-23d4-4a80-b066-edca32ee158f` | Composer |
| lyricist | `3e48faba-ec01-47fd-8e89-30e81161661c` | Lyricist |
| arranger | `d3fd781c-5894-47e2-8c12-86cc0e2c8d08` | Arranger |

Generic writer `a255bca1-b157-4518-9108-7b147dc3fc68` is deliberately not
promoted to composer or lyricist.

Accepted Recording relationship identities:

| Type | UUID | Canonical role |
| --- | --- | --- |
| producer | `5c0ceac3-feb4-41f0-868d-dc06f6e27fc0` | Producer |
| arranger | `22661fb8-cdb7-4f67-8385-b2a8be6c9f0d` | Arranger |
| conductor | `234670ce-5f22-4fd0-921b-ef1662695c5d` | Conductor |
| performer | `628a9658-f54c-4142-b0c0-95f031b544da` | Performer |
| instrument | `59054b12-01ac-43ee-a618-285fd397e461` | Performer plus instrument |
| vocal | `0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa` | Performer plus vocal attribute |
| performing orchestra | `3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb` | Performer/ensemble |

An explicit `guest` relation attribute additionally creates Guest Artist
participation. Vocal does not imply featured or guest.

Accepted Release relationship identities:

| Type | UUID | Canonical role |
| --- | --- | --- |
| producer | `8bf377ba-8d71-4ecc-97f2-7bb2d8a2a75f` | Producer |
| conductor | `9ae9e4d0-f26b-42fb-ab5c-1149a47cf83b` | Conductor |
| performer | `888a2320-52e4-4fe8-a8a0-7a4c8dfde167` | Performer |
| instrument | `67555849-61e5-455b-96e3-29733f0115f5` | Performer plus instrument |
| vocal | `eb10f8a0-0f4c-4dce-aa47-87bcb2bc42f3` | Performer plus vocal attribute |
| performing orchestra | `23a2e2e7-81ca-4865-8d05-2243848a77bf` | Performer/ensemble |

## Discogs parsing and scope

Discogs reuses the same concrete Release response used by V2 and Wave 1, with
zero extra requests. Only `extraartists` rows with blank `tracks` are eligible,
and they remain Release-scoped. Nonblank `tracks` and tracklist extraartists are
not global.

Accepted whole normalized roles are Producer, Conductor, Featuring, Guest, and
the explicit instruments Acoustic Guitar, Bass, Bass Guitar, Drums, Electric
Guitar, Guitar, Keyboards, Orchestra, Percussion, Piano, Synthesizer, and
Vocals. `anv` is credited-as. Vague substrings and compound roles are not
accepted. `Written-By` is not composer because it does not distinguish music
from words.

The current provider boundary has no selected medium/occurrence map. Discogs
Recording credits are therefore deferred instead of using title matching,
positional zip, or unsafe multidisc assignment.

## Resolution

`credit_resolution.py` is independent of the generic and release-catalog
resolvers. Primary and compatible secondary evidence are structurally unioned.
Identical units corroborate; different instruments, roles, scopes, source
entities, and MBIDs remain independent. Fallback is suppressed when stronger
eligible evidence exists.

Existing state is monotonic. Equal or incoming-subset evidence is KEEP. A safe
superset or nonconflicting partial overlap proposes the union. Provider omission
produces no decision and never deletion. Ordered artist-credit disagreement is
REVIEW because arbitrary union would destroy joins and order.

## Persistence and query projections

Complete accepted state is stored in normalized, versioned
`noqlenmeta_credit*` tables inside the active beets library SQLite database.
Rows reference existing Item or Album IDs; no Items/Albums are duplicated and
no second library database exists. Relations, attributes, credited-as variants,
artist-credit nodes, and provenance use separate typed columns/rows rather than
JSON or DSV blobs.

Tables are created lazily on the first credit apply. Reads against a V2 library
without the tables return absent state without mutation. Unknown schema versions
fail closed. Inserts are append-only by structural key; provider omission never
deletes rows. State is reconstructible from providers.

Queryable projections are:

- native Item `composers`/`composers_ids`, `lyricists`/`lyricists_ids`, and
  `arrangers`/`arrangers_ids`;
- typed Item and Album `producers`, `conductors`, `performers`, and
  `featured_artists` name lists;
- complete role/scope/instrument and artist-credit data in structured state.

Name views explicitly omit instruments rather than delimiter-encoding them.

## Importer and existing library

Importer enrichment runs only after beets selected `Action.APPLY`. Recording
and Work credits use the exact selected Recording; Release credits use the exact
selected Release. Accepted structured changes are queued by MBID and persisted
by `item_imported`/`album_imported` after beets creates database rows. Hooks do
not acquire or resolve.

`beet nm QUERY`, `--all`, strict/partial apply, and optional write use the same
prepared plans. Existing-library Item and Album plans stay separate, so Release
credits never become Recording credits. A second run reads structured current
state and is a no-op when evidence is unchanged.

## Native and file targets

The supported range was programmatically audited at beets 2.12.0 and latest
supported 2.x (2.13.1), both with MediaFile 0.17.0.

| Concept | beets database | File behavior |
| --- | --- | --- |
| Composer names | Native plural | MediaFile plural composer; one value across tested formats, multiple MP3 blocked for ID3v2.3 safety |
| Composer IDs | Native plural | No MediaFile target |
| Lyricist names/IDs | Same native split | Names only under the same safety rule |
| Arranger names/IDs | Same native split | Names only under the same safety rule |
| Producer/conductor | Typed name view plus state | BLOCKED |
| Performer/instrument | Typed name view plus state | BLOCKED, including MP4 |
| Featured/guest | Typed name view plus state | BLOCKED; primary artist tags untouched |
| Structured artist credit | Structured state | BLOCKED; primary artist tags untouched |

No credit `NOQLEN_*` audio tag exists. Candidate-copy, snapshots, unrelated-tag
verification, atomic replacement, recovery, and stale-state checks remain the
file safety boundary.

## Acquisition budget and failure isolation

For enabled Wave 1 plus credits, each Recording has at most one sufficient
Recording acquisition, each needed Work at most one sufficient profile-aware
acquisition, the Release at most one sufficient acquisition, and Discogs at
most one concrete Release acquisition. Write performs zero provider calls.

Recording relationship failure does not erase ISRC/Work/date or existing
credits. Work relationship failure does not erase Work identity/ISWC already
available. Discogs credit parsing failure does not erase catalog candidates.
Malformed individual relations are skipped locally. Failure never means empty
replacement.

## Explicit deferrals

- Discogs Recording/track credits until exact selected occurrence mapping is
  available at the provider boundary.
- MusicBrainz Recording composer/lyricist authority because no explicit audited
  artist-Recording relationship asserts those roles.
- Automatic primary artist or album-artist correction.
- Mixing, mastering, recording-engineer taxonomy and all Wave 2B features.
- Deep classical Work hierarchy and naming rules.
