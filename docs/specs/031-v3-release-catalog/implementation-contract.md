# V3 Wave 1A Release Catalog Implementation Contract

## Status and boundary

Wave 1A supplied the internal Release/Release Group catalog pipeline. The 032
Wave 1 contract now supersedes its former internal-only integration boundary and
wires these values into normal importer, CLI, database and audited file targets.

The implemented pipeline is:

```text
MetadataEvidence -> field authority -> catalog resolution -> ChangePlan
-> release catalog target plan
```

`plan_release_catalog()` is the pure internal composition boundary. It accepts
already acquired evidence and current canonical values, then returns immutable
decisions, the shared ChangePlan, and the target plan. It performs no provider
call, configuration lookup, mutation or file operation.

## Fields

- `date`: canonical partial date of the exact edition, asserted on Release.
- `original_date`: canonical first release date of the Release Group.
- `year`: compatibility projection derived only from `date.year` in V3.
- `original_year`: compatibility projection derived only from
  `original_date.year`; it has no provider capability or authority.
- `release_type`: one controlled MusicBrainz primary Release Group type.
- `release_secondary_types`: ordered, deduplicated controlled Release Group
  secondary types, kept separate from the primary type.
- `release_status`: one controlled MusicBrainz Release status: `Bootleg`,
  `Cancelled`, `Expunged`, `Official`, `Promotion`, `Pseudo-Release`, or
  `Withdrawn`. Matching is case-insensitive; unknown or malformed values emit
  no evidence.
- `edition`: one controlled explicit Release designation.

## Date precision

Canonical dates use `PartialDate` and preserve only known components. Accepted
forms are `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-??-??` and `YYYY-MM-??`.
Unknown month/day components are omitted, never converted to January or day 1.
Impossible calendar dates and malformed precision are ignored.

Partial dates are compatible when every component known by both values agrees.
Compatible evidence resolves to the greater safe precision. Material year,
month or day disagreement is `REVIEW`. A compatible existing value with greater
precision is retained; compatible more-precise evidence may enrich a less
precise existing value.

## Evidence sources and calls

### MusicBrainz

MusicBrainz uses only an exact established Release MBID. The V3 method reuses
the same release payload and command cache as V2 enrichment.

- Release `date` supplies `date`.
- Release `status` supplies `release_status`.
- nested Release Group `first_release_date`, `primary_type`, and
  `secondary_types` supply the Release Group fields when complete.
- an exact cached Release Group lookup is used only when a requested Release
  Group field is missing and a valid group MBID is known from the nested Release
  payload or an explicitly supplied namespaced release-group identity.
- absent Release Group identity never causes search or speculative lookup.
- one Release Group response serves all requested Release Group fields.
- supporting lookup failure removes only missing Release Group evidence and
  does not discard Release date/status evidence.

The V2 `get_candidates()` method, includes, output and ordinary call count are
unchanged. No search, relationship include, credit traversal or identity repair
is introduced.

### Discogs

Discogs reuses the concrete Release selected by the existing direct-ID/search
adapter and performs no additional request.

- structural `released` supplies secondary `date` evidence;
- exact controlled format descriptors may supply primary `edition` evidence.

Approved edition values are Deluxe, Limited, Special, Collector's,
Anniversary, and Expanded Edition. Parsing is whole-value only. Title, notes,
country, format name, weight, gatefold, reissue, repress, remaster, mono/stereo,
catalog number and arbitrary free text do not create edition evidence. Multiple
different approved descriptors remain separate evidence and resolve to
`REVIEW`, never concatenation.

### iTunes

iTunes parses valid `releaseDate` from the same collection response already
selected by its direct collection, UPC or bounded search path. It is fallback
evidence for `date`. No endpoint, explicitness, artwork or availability mapping
is added.

## Authority

| Field | Entity | MusicBrainz | Discogs | iTunes |
| --- | --- | --- | --- | --- |
| `date` | Release | Primary | Secondary | Fallback |
| `original_date` | Release Group | Primary | Ineligible | Ineligible |
| `release_type` | Release Group | Primary | Ineligible | Ineligible |
| `release_secondary_types` | Release Group | Primary | Ineligible | Ineligible |
| `release_status` | Release | Primary | Ineligible | Ineligible |
| `edition` | Release | Ineligible | Primary | Ineligible |

`original_year` is derived and therefore has no authority row. Provider-local
confidence is an eligibility threshold, not a cross-provider score. Primary and
secondary compatible evidence can corroborate or increase date precision;
material disagreement remains visible as `REVIEW`. Fallback participates only
when no primary or secondary evidence resolves the field. There is no provider
vote.

## Resolution and ChangePlan

The Wave 1A resolver handles only `EXCLUSIVE` and `MULTIVALUE` field contracts.
Taxonomy, identity, AcoustID, lyrics, artwork and audio retain their specialized
resolvers.

The existing ChangePlan accepts V2 `MetadataCandidate` or V3
`MetadataEvidence` provenance. V3 changes retain all contributing evidence when
values are safely coalesced. Resolution happens before ChangePlan construction;
mapping performs no acquisition or resolution.

## Targets

- `date` maps only known components to native `year`, `month`, and `day`.
- `original_date` maps only known components to native `original_year`,
  `original_month`, and `original_day`.
- `release_type` maps losslessly to native `albumtype`.
- `release_status` maps losslessly to native `albumstatus`.
- `release_secondary_types` persists separately as an Album multivalue typed DB
  field. Native combined `albumtypes` is projected only when the accepted
  primary type is present in the same plan.
- `edition` persists only as an Album string typed DB field.

Independent V3 `year` or `original_year` changes are rejected by target
planning, preventing contradictory rich-date and scalar-year truths. No unknown
date component is materialized. No file target or private audio tag is created
for edition or secondary-type preservation in this slice.

## Deliberate deferrals

Wave 1A does not add public configuration or CLI wiring. It does not implement
ISRC, ISWC, Work identity, recording date, credits, aliases, explicitness,
vocal language, instrumental state, lyrics sidecars, additional artwork, audio
features, Deezer, identity repair, AcoustID changes, file writing, or Wave 1B.
