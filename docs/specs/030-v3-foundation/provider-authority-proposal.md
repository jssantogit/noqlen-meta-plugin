# Proposed V3 Provider Authority Matrix

## Semantics

This is the first Wave 0A proposal, not production policy. It does not modify
`resolver.py` or public configuration.

- **primary:** strongest eligible source for the field at the asserted scope.
- **secondary:** independently eligible evidence; may win when primary is absent
  or improve a field-specific decision.
- **fallback:** acquire only while the field remains unresolved.
- **corroboration-only:** may validate/review but cannot create the canonical
  value alone.
- **ineligible:** must not contribute to that field/scope.

Unlisted combinations are ineligible. `MB` means MusicBrainz ordinary/semantic
enrichment, not its separate four-MBID repair subsystem. AcoustID is listed only
in the identity-evidence section and never enters ordinary provider resolution.

## Catalog, identifiers, and semantics

| Field/concept | Asserted scope | MB | Discogs | Last.fm | iTunes | LRCLIB | CAA | Deezer candidate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current edition date/year | Release | primary | secondary | ineligible | fallback | ineligible | ineligible | fallback, deferred operationally |
| Original date/year | Release Group | primary | secondary when Master lineage is proven | ineligible | ineligible | ineligible | ineligible | ineligible |
| Recording date | Recording | primary when relationship/date evidence is explicit | corroboration-only if track-scoped and unambiguous | ineligible | ineligible | ineligible | ineligible | ineligible |
| Release type | Release Group | primary | secondary | ineligible | fallback | ineligible | ineligible | fallback, deferred operationally |
| Secondary release types | Release Group | primary | secondary after controlled normalization | ineligible | ineligible | ineligible | ineligible | ineligible |
| Release status | Release | primary | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Edition | Release | secondary | primary for explicit edition/format facts | ineligible | fallback only for explicit structured text | ineligible | ineligible | defer; no structured evidence observed |
| Labels | Release | secondary | primary | ineligible | fallback digital label | ineligible | ineligible | secondary digital label, deferred |
| Catalog numbers | Release | secondary | primary | ineligible | ineligible | ineligible | ineligible | ineligible |
| Barcode/UPC | Release | secondary | primary | ineligible | secondary/match evidence | ineligible | ineligible | secondary/match evidence, deferred |
| Country | Release | secondary | primary | ineligible | ineligible | ineligible | ineligible | ineligible |
| Media/formats | Release/Medium | secondary | primary | ineligible | ineligible | ineligible | ineligible | ineligible |
| ISRC | Recording | primary after established Recording MBID | secondary/corroborating after exact track-position mapping | ineligible | defer until official track shape proves it | ineligible | ineligible | defer |
| Work/MB Work ID | Recording -> Work | primary | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| ISWC | Work | primary | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Genres | Recording/Release/Artist | primary native MB genre evidence; secondary community tags | primary structured release evidence | fallback/corroboration community evidence | fallback broad release genre | ineligible | ineligible | ineligible; no incremental quality |
| Styles | Release/Recording/Artist | secondary classified community evidence | primary structured release styles | fallback/corroboration classified tags | ineligible | ineligible | ineligible | ineligible |
| Moods | Recording/Release/Artist | primary classified evidence at strongest eligible scope | ineligible | secondary/fallback classified evidence | ineligible | ineligible | ineligible | ineligible |
| Vocal languages | Recording | primary Work/relationship evidence, with field-specific validation | ineligible | ineligible | ineligible | secondary only if a later reliable lyric-language derivation exists | ineligible | ineligible |
| Instrumental | Recording | primary relationship/performance attributes | ineligible | ineligible | ineligible | secondary for explicit `instrumental=true`; never false-by-absence | ineligible | ineligible |
| Explicitness | Recording/track | ineligible | ineligible | ineligible | primary/fallback digital track evidence | ineligible | ineligible | secondary/fallback, deferred pending false/clean semantics |

## Credits and title structure

| Field/concept | Asserted scope | MB | Discogs | Last.fm | iTunes | LRCLIB | CAA | Deezer candidate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Composer/lyricist | Work/Recording | primary structured relationships | secondary when track-scoped role is explicit | ineligible | ineligible | ineligible | ineligible | ineligible |
| Producer | Recording or Release | primary when relationship scope is explicit | secondary/primary for edition-specific release or track credit | ineligible | ineligible | ineligible | ineligible | ineligible |
| Arranger | Work/Recording | primary structured relationship | secondary when scope/role is explicit | ineligible | ineligible | ineligible | ineligible | ineligible |
| Conductor | Recording/Release | primary | secondary when scope is explicit | ineligible | ineligible | ineligible | ineligible | ineligible |
| Performers/instruments | Recording/Release | primary structured relationships/attributes | secondary scoped `extraartists` | ineligible | ineligible | ineligible | ineligible | ineligible |
| Featured/guest artists | Recording/Release | primary structured artist credit/relationships | secondary when role and track scope are explicit | ineligible | ineligible | ineligible | ineligible | defer contributor roles |
| Structured artist credits | Recording/Release | primary | secondary only for corroboration/edition credits | ineligible | corroboration-only names/IDs | ineligible | ineligible | corroboration-only/defer |
| Alternate/localized titles | Recording/Release/Work | primary aliases/pseudo-release evidence | secondary explicit alternate titles only | ineligible | ineligible | ineligible | ineligible | ineligible |
| Script | Release/main title | primary | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Transliteration | Alias/pseudo-release | primary typed alias/relationship evidence | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Track version/mix | Recording/track | primary relationship/attribute evidence | secondary when explicit track title/credit structure establishes it | ineligible | secondary explicit store field/title only | corroboration-only matching signal | ineligible | defer `title_version` semantics |

## Lyrics, artwork, and audio

| Field/concept | Asserted scope | MB | Discogs | Last.fm | iTunes | LRCLIB | CAA | Deezer candidate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Plain lyrics | Recording | ineligible | ineligible | ineligible | ineligible | primary | ineligible | ineligible |
| Synced lyrics | Recording | ineligible | ineligible | ineligible | ineligible | primary | ineligible | ineligible |
| Front artwork | Release asset | ineligible as bytes | ineligible as typed authority | ineligible | fallback, subject to content terms | ineligible | primary for established MB Release | fallback after CAA, deferred operationally |
| Back artwork | Release asset | ineligible | ineligible because image class is not Back | ineligible | ineligible | ineligible | primary | ineligible |
| Disc artwork | Medium asset | ineligible | ineligible without typed medium/disc evidence | ineligible | ineligible | ineligible | primary only when Medium type is unambiguous; disc index may remain unresolved | ineligible |
| BPM | Recording | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible | defer; unproven | 
| Key | Recording | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Energy | Recording | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |
| Danceability | Recording | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible | ineligible |

Existing valid BPM/Key/Energy/Danceability values and future local analysis are
not providers. They participate in each audio field's specialized resolver with
method/version/confidence; derived buckets are recalculated and have no provider
authority row.

## Identity authority remains separate

| Evidence | Scope | Role |
| --- | --- | --- |
| Complete MusicBrainz release candidate | Release plus assigned recordings/occurrences | Sole source of the four-field MB identity; structural primary |
| Existing MBIDs | Current target state | Acquisition/comparison only; never positive score |
| Decisive AcoustID result | Recording compatibility | Corroboration/filter only after structural assignment |
| Discogs/iTunes/Deezer/LRCLIB/CAA/Last.fm | Any | Ineligible for MusicBrainz identity repair |

AcoustID cannot write MBIDs, select a release occurrence, add score or rescue a
weak/ambiguous candidate.

## Non-obvious decisions

- **MusicBrainz versus Discogs date:** exact MB Release date is primary because
  enrichment is anchored to the selected MB edition. Discogs is secondary for
  the conservatively matched Discogs edition and creates REVIEW on material
  incompatibility rather than an arbitrary winner.
- **Original date:** MusicBrainz Release Group first-release semantics are the
  primary candidate. Discogs Release year/date alone is an edition date; Master
  lineage must be established before it can contribute original-date evidence.
- **Edition:** Discogs has the strongest edition-specific format/free-text
  surface, but semi-structured text requires controlled normalization. MB
  disambiguation/title/format can contribute, not automatically concatenate.
- **Discogs credits:** it may be strong for the exact physical edition but scope
  text is not always machine-safe. It cannot automatically project release
  credits onto recordings.
- **iTunes/Deezer explicitness:** track-level digital flags are eligible;
  album-level flags are summaries only. Missing or undocumented false values
  remain unknown.
- **LRCLIB instrumental:** explicit true can corroborate instrumental state;
  false or absent lyrics cannot establish vocal state.
- **CAA Medium:** it identifies physical-media artwork but not disc number.
  Multidisc assignment may remain REVIEW even though CAA is the source
  authority.
- **Last.fm:** no extra V3 role was created. Its defensible value remains
  taxonomy-filtered community semantics.
- **Deezer:** field-level roles are proposed, but provider adoption is DEFER
  until access, terms, rate-limit and enum semantics are reviewed.

## Matrix validation required in Wave 0B

- Every authority entry references a registered field and provider capability.
- Every capability has an asserted entity/scope and identity prerequisite.
- Unlisted combinations are ineligible.
- Corroboration-only sources cannot create values.
- Fallback acquisition stops after sufficient primary/secondary resolution.
- Specialized resolvers remain responsible for multivalue, taxonomy, assets,
  lyrics, audio and identity conflict rules.
