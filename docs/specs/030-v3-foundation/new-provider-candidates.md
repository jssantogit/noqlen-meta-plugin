# New Provider Candidates

## Decision summary

**Deezer: DEFER as a production provider; retain as the leading candidate.**

The observed album shape can close three concrete gaps: exact current-edition
date, track explicitness, and high-resolution Front artwork fallback. It also
offers strong matching/provenance signals in one album response. Adoption is
not approved in Wave 0A because official endpoint schemas are login/terms gated,
no public numeric rate limit was found, terms/access stability need human
review, and important enums and `false` explicitness semantics remain
undocumented in the accessible material.

This evidence does not justify deep Spotify, Beatport or other audits. Remaining
V3 gaps are primarily MusicBrainz relationship and Discogs edition/credit gaps,
not missing digital-store breadth.

## Evidence and bounded live observation

Official pages consulted:

- <https://developers.deezer.com/api>
- <https://developers.deezer.com/api/album>
- <https://developers.deezer.com/api/track>
- <https://developers.deezer.com/api/search>
- <https://developers.deezer.com/api/oauth>
- <https://developers.deezer.com/guidelines>
- <https://developers.deezer.com/termsofuse>

Endpoint-reference pages required login and acceptance of the simple API terms,
so they did not provide a public schema or rate-limit contract during this
audit. The accessible terms state that access may be modified, restricted or
removed without notice and describe non-commercial use. Applicability to the
project and persistent artwork use requires human review.

One non-mutating public call was made, and no fixture was retained:

| Property | Observation |
| --- | --- |
| Time | `2026-08-12T15:05:18+00:00` |
| Request | `GET https://api.deezer.com/album/302127` |
| Public catalog object | Daft Punk, *Discovery* |
| Authentication | None |
| Status | HTTP 200 JSON |

Observed album fields included `id`, `title`, `upc`, artist and contributor IDs
and names, `label`, `nb_tracks`, `duration`, `release_date`, `record_type`,
availability, explicitness fields, cover URLs from small through XL, and an
embedded track list. Tracks included ID, title, `title_short`, `title_version`,
duration, rank, explicitness, artist and album identity. `cover_xl` used a
1000x1000 representation.

The response did not expose MBIDs, ISRC/ISWC, Work, original/recording date,
secondary type/status/edition, catalog number/country/physical media,
Back/Medium art, credits beyond contributor role, languages, lyrics, BPM, Key,
Energy or Danceability. One response cannot prove that another endpoint never
exposes them.

## Matching assessment

If later adopted, acquisition must remain behind established identity:

1. Direct persisted Deezer album ID when available.
2. Search only for candidate discovery.
3. Exact normalized album artist/title validation.
4. Prefer exact UPC agreement.
5. Validate edition date, track count, ordered titles and durations.
6. Reject conflicting UPC/date and multiple surviving editions.
7. Map tracks by position, normalized title and duration; retain Deezer track ID
   as provider-local provenance.
8. Never let Deezer agreement repair or strengthen MusicBrainz identity.

Strengths are album/track IDs, UPC, complete small-album track list, durations,
track count and title/version slots. Weaknesses are no observed MB cross-link,
regional catalog variation, digital-edition ambiguity, inaccessible official
search contract, and no observed disc/track-number fields in this response.

## Field decisions

`ADOPT` means the observed shape justifies a narrow eventual role if operational
access is approved. `DEFER` means useful potential lacks contract/semantic
evidence. `REJECT` means Deezer should be ineligible for that V3 concept based
on the audit.

| Field/concept | Decision | Proposed role and reason |
| --- | --- | --- |
| Deezer album/track/artist IDs | ADOPT | Provider-local direct lookup, cache, matching and provenance only. |
| MusicBrainz IDs | REJECT | Not observed; never infer or repair. |
| AcoustID | REJECT | Wrong subsystem and no fingerprint evidence. |
| UPC/barcode | ADOPT | Matching and secondary/corroborating release evidence. |
| ISRC | DEFER | Not in album/embedded-track response; official track schema inaccessible. |
| ISWC/Work | REJECT | No Work entity or relationship evidence. |
| Current edition date/year | ADOPT | Exact `release_date` closes current year-only adapter behavior; fallback after exact identity. |
| Original release date/year | REJECT | One date concept cannot be reinterpreted as original date. |
| Recording date | REJECT | No evidence. |
| Primary release type | ADOPT | `record_type` supports fallback digital classification after enum verification. |
| Secondary release types | REJECT | No structured evidence. |
| Release status | REJECT | Availability is regional service state, not release status. |
| Edition | DEFER | No structured field; no title-keyword inference. |
| Label | ADOPT | Secondary digital-edition evidence; incremental coverage is modest. |
| Catalog number/country/physical media | REJECT | Not observed; request region is not release country. |
| Track count/album duration | ADOPT | Matching evidence, not new canonical metadata. |
| Availability/readability/rank/fans | REJECT | Dynamic/regional/popularity state is outside canonical V3 metadata. |
| Genre | REJECT | One broad album genre adds no material gain over current taxonomy-aware sources. |
| Styles/moods/languages/script/transliteration | REJECT | Not observed. |
| Instrumental | REJECT | Not observed; cannot infer from title or lyrics absence. |
| Track version/mix | DEFER | `title_version` exists structurally but was empty and undocumented. |
| Main title/title short | ADOPT | Matching only; no automatic title takeover. |
| Track explicitness | ADOPT | Clearest unique gain; preserve track scope. |
| Clean classification | DEFER | Confirm whether false is affirmative clean rather than unknown. |
| Unknown explicitness | ADOPT | Missing/malformed/unverified always maps to unknown. |
| Album explicit summary | ADOPT | Summary evidence only; never propagate one album flag to all tracks. |
| Numeric explicit-content enums | DEFER | Observed but official enumeration inaccessible. |
| Primary artist | ADOPT | Matching/participation evidence; no artist-name takeover. |
| Featured/guest/structured credits | DEFER | Contributor structure exists, but only Main observed and vocabulary/joins are undocumented. |
| Composer/lyricist/producer/arranger/conductor/performers | REJECT | Not observed. |
| Plain/synced lyrics | REJECT | No lyric content. |
| Lyrics matching signals | ADOPT | Track ID/title/album/duration can corroborate matching, not provide lyrics. |
| Front artwork fallback | ADOPT | Named sizes through 1000x1000; only after CAA definitive absence and terms review. |
| Original-resolution artwork | DEFER | XL is 1000x1000; no source-original guarantee. |
| Back/disc/gallery artwork | REJECT | No typed assets. |
| Artwork identity evidence | REJECT | Prohibited by V3. |
| Artwork persistence | DEFER | Storage/use/attribution terms require review. |
| BPM | DEFER | Not observed in embedded tracks; full track contract inaccessible. |
| Key/Energy/Danceability | REJECT | Not observed. Rank is not an audio feature. |
| Derived audio buckets | REJECT | Must derive from canonical audio values. |
| Track duration | ADOPT | Matching/version discrimination only. |
| Preview audio | REJECT | Unnecessary content boundary and no V3 metadata gap closed. |
| Classical/technical metadata | REJECT | No Work, movement, instrument or role evidence observed. |

## Incremental gain over current providers

- **Date:** real gain because current MusicBrainz/Discogs/iTunes adapters emit
  only year, although improving those adapters may already close much of it.
- **Explicitness:** material gap; current providers emit none. iTunes can also
  supply it and has more accessible official field documentation, so Deezer is
  not uniquely required.
- **Front artwork:** useful 1000x1000 fallback, but CAA remains primary and
  iTunes is another fallback candidate. Deezer does not close required Back.
- **Matching:** one album response can potentially serve date, type, UPC,
  explicitness, IDs, durations and cover metadata, which is cost-efficient.
- **Other V3 domains:** no material incremental value established.

## Operational decision gate

Before Deezer implementation, require:

1. Human review of API terms, intended-use compatibility, artwork storage and
   attribution requirements.
2. Accepted-access review of album, track, search, pagination, errors and rate
   limits.
3. Official semantics for `explicit_lyrics`, especially false/clean/unknown,
   plus `explicit_content_*`, `record_type` and contributor roles.
4. Confirmation of regional/cache key dimensions and anonymous versus token
   access.
5. Offline contract coverage for ambiguity, regional absence, large/multidisc
   track lists, tri-state explicitness and 429 behavior.

Until those gates pass, the aggregate provider decision is **DEFER**, even for
fields marked ADOPT. No Deezer adapter, config or fixture belongs in Wave 0A.
