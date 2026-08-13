# V3 Wave 1 Recording and Work Identifier Contract

## Status and boundary

Wave 1 is integrated into ordinary importer and existing-library enrichment.
It uses one immutable `ChangePlan` for each Release or Track and does not add
Wave 2 credits, aliases, localized titles, versions, languages, explicitness,
artwork, audio features, identity repair, AcoustID behavior or private tags.

## Recording identity gate

Recording enrichment requires the exact canonical MusicBrainz Recording MBID
already selected by beets. There is no Recording search, title/artist match,
ISRC lookup or AcoustID shortcut. Release and Release Group enrichment likewise
uses only established exact IDs. Existing IDs are acquisition anchors, never
positive evidence for the separate four-MBID repair subsystem.

## ISRC

MusicBrainz Recording is primary. Every structurally valid ISRC is normalized,
deduplicated and preserved in one `IdentifierCollection`. Empty current state
accepts exact evidence; an incoming strict superset safely enriches; an incoming
subset keeps the existing superset; partial overlap or disjoint sets require
REVIEW. Provider absence and lookup failure never propose deletion.

The queryable Item field `isrcs` always stores accepted plural state. Exactly
one value may also project to native `isrc`; multiple values never select an
arbitrary first value.

## WorkReference

`WorkReference` preserves one exact structured Recording-to-Work relationship:

```text
mbid, optional title, relation type, optional relation type ID,
attributes, optional ordering key
```

The Work MBID and relation type ID are canonical UUIDs. Empty titles are not
accepted. Attributes are retained without interpreting live, instrumental,
cover, demo, karaoke or other Wave 2 semantics. Relations deduplicate by Work
and relation identity and sort by explicit ordering key, then stable identity
tie-breaks. Works are never inferred or searched by title. Existing
`mb_workid`/`mb_workids` values are current state, not proof of a relationship.

The queryable Item field `mb_workids` stores all accepted Work IDs. Exactly one
Work may also project to native `mb_workid`; its safe relation title may fill
native `work`. Multiple Works are never flattened and no parallel work-title
list is stored.

## ISWC

Each Work obtained from a valid Recording relationship is looked up exactly by
MBID. One cached Work response can serve ISWC now and future Work fields later.
All valid ISWCs are retained in Work-scoped evidence and projected in aggregate
to queryable Item `iswcs`. No ISWC private file tag exists.

A missing or failed Work lookup affects only supporting data for that Work. It
does not discard Recording ISRC, the Work reference itself, or successful
sibling Works. Provider failure never means deletion.

## recording_date

MusicBrainz is primary only for structurally explicit Recording relationship
evidence. This implementation accepts an audited `recorded at` relationship
only when its begin and end parse to the same safe `PartialDate`. It rejects
intervals, one-sided dates, divergent dates, inferred Event/Place names and any
release date. Recording `first_release_date` is explicitly ineligible.

Safe values persist only as queryable Item `recording_date` text in canonical
ISO partial-date form: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`. There is no DATE/TDRC
or other embedded file projection. Coverage is intentionally limited; no safe
payload means no evidence and is not an error. Multiple different safe dates
require REVIEW.

## Authority and resolution

MusicBrainz exact Recording evidence is primary for `isrcs`, `works` and
`recording_date`; exact Work evidence is primary for `iswcs`. No provider vote
is used. V2 ordinal `resolution.authority` is not reinterpreted as V3 role
ordering. The specialized resolver preserves existing values, permits only safe
superset enrichment, and routes material conflict to REVIEW.

## Wave 1 release integration

Release fields are `date`, `original_date`, `release_type`,
`release_secondary_types`, `release_status` and `edition`. `date=true` makes
the V3 partial date canonical and suppresses competing V2 provider `year`
decisions; year is projected from `date.year`. With `date=false, year=true`, V2
year behavior is unchanged. Release type projection uses effective accepted
primary and secondary state, including KEEP/PROPOSE combinations.

MusicBrainz, Discogs and iTunes expose shared release enrichment results so one
concrete acquisition supplies V2 candidates and V3 evidence. Expected counts
are one MusicBrainz Release response, plus at most one exact Release Group
support response only when requested missing fields require it; one Discogs
concrete Release acquisition; and one iTunes collection acquisition path.

## Targets and workflow

Release and original dates project only known native date components. Release
type and status use audited native targets. Separate secondary types, edition,
plural identifiers and recording date use typed database targets where needed.
Mapping performs no acquisition or resolution.

Preview is non-mutating. Apply stores accepted database-safe fields. Partial
apply retains REVIEW/BLOCKED fields while applying accepted units. Optional
write uses the same plan and performs no provider lookup. Dates, original dates,
release type/status, one ISRC and one Work ID are written only through audited
native MediaFile targets. Multiple ISRCs/Works, ISWC, recording date, edition
and semantically unsupported secondary-type projections are file blockers, not
reasons to discard safe database state.

Importer enrichment runs only after beets selected and authorized its match;
beets remains owner of matching and file lifecycle. Existing-library `beet nm`
uses the same authority for preview, strict apply, partial apply and write.

## V2 compatibility and explicit deferrals

The four MusicBrainz identity fields, AcoustID subsystem, V2 semantic fields,
legacy `year` mode and existing private compatibility tags remain separate and
unchanged. This wave does not implement Discogs track-position ISRC, composer,
lyricist, producer, arranger, conductor, performers, featured artists, aliases,
transliteration, track versions, explicitness, vocal language, instrumental
state, lyrics V3, additional artwork, audio features, Deezer or deep classical
hierarchy.
