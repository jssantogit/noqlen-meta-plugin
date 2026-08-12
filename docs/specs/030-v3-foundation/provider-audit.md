# V3 Current Provider Audit

## Status and method

This is the Wave 0A decision record. It changes no provider, resolver, target,
configuration, or production behavior. The code baseline is
`55c92e6a0672cd6fbf5f1e714f60649b45bd86ad` on `main`.

The audit prioritizes production adapters and tests, then accepted ADRs/specs,
then provider-maintained documentation. No user-library data or credentials
were used. The only live API observation made during Wave 0A was the bounded
Deezer call recorded in `new-provider-candidates.md`; no current-provider live
call was needed. No fixture was added because this documentation-only audit did
not introduce a parser contract.

Key project references are `providers/base.py`, `providers/specs.py`,
`provider_cache.py`, ADRs 0012, 0014, 0016, 0020, and 0025, specs 016, 018, 020,
024, and 029, and the V3 Core Design.

## Cross-provider findings

- Ordinary providers return synchronous `MetadataCandidate` values and never
  write. Expected external failure is `ProviderError`; contract/programming
  defects remain visible as `ProviderContractError`.
- Generic scopes are only Release, Track, and Artist. MusicBrainz identity,
  artwork, local audio analysis, and AcoustID already have separate boundaries.
- Numeric `confidence` is provider-local acquisition/match quality. It is not a
  universal score. Current resolution applies a default 0.8 threshold and then
  field authority.
- MusicBrainz ordinary and semantic enrichment reuse a release payload and a
  command cache. Other caches are adapter-local. There is no persistent,
  methodology-versioned provider cache or command-wide acquisition budget.
- Provider absence/failure creates no deletion proposal. This already satisfies
  the V3 rule that provider failure is not deletion.
- Current checked-in fixtures do not cover V3 relationships, partial full
  dates, typed artwork beyond front, or richer digital metadata. Add fixtures
  only with the parser work that needs them.

## MusicBrainz release enrichment

### Current contract

- **Files:** `providers/musicbrainz.py`, shared parsing/cache support in
  `providers/musicbrainz_semantic.py` and `provider_cache.py`; tests in
  `tests/test_musicbrainz_provider.py`; fixture
  `tests/fixtures/musicbrainz/release.json`.
- **Scope and identity:** exact Release MBID from beets-selected context. It is
  enrichment, not matching, and never searches or repairs identity.
- **Method:** beets `MusicBrainzAPI.get_release()` with `labels`, `media`,
  `genres`, `tags`, `recordings`, and `artist-credits` includes.
- **Extracted:** label names, catalog numbers, barcode, country, leading year
  from release date, and media formats. Release genres/tags feed the semantic
  path.
- **Ignored from the current payload:** release title, status, release group,
  structured artist credit, track/recording data, packaging and text
  representation. `recordings` and `artist-credits` are requested but ordinary
  normalization does not consume them.
- **Match/confidence:** response MBID must equal the requested MBID; fixed 0.99
  confidence. Missing/malformed/conflicting context IDs cause no request.
- **Failure:** missing gives no evidence; malformed/mismatched payload or
  transport error becomes sanitized `ProviderError`.
- **Operations:** beets owns User-Agent, timeout, retry and MusicBrainz pacing.
  The official limit is an average of one request/second per source IP. Valid
  and definitive-missing exact payloads are command-cached; failures are not.

### V3 capacity and cost

- Release payload can defensibly supply current partial date, release status,
  release text language/script, structured artist credits, and release facts.
- Release-group identity is needed for primary/secondary types and first release
  date. It may be nested or require an exact release-group lookup depending on
  include completeness.
- Recording lookup can request `isrcs`, artist credits, releases/release groups,
  and relationships. Recording-to-Work plus target-level relationships can be
  requested using `work-rels+work-level-rels+artist-rels`; this is one richer
  call but linked subqueries are bounded to 25 entities.
- Work lookup supplies ISWC, lyric languages, aliases, and Work-to-Artist
  composer/lyricist/writer/arranger relationships. Complete aliases or credits
  can justify one exact Work call when nested data is incomplete.
- Recording-to-Artist relationships can supply producer, conductor, performer,
  instrument/vocal attributes, arranger, engineer, mix, recording engineer,
  programming, and editor roles. Preserve type IDs, attributes, credited-as
  text, direction, and dates; do not reduce instruments to role strings.
- Recording-to-Work performance attributes can support cover, live, demo,
  instrumental, karaoke, medley, and partial evidence. Recording-to-recording
  relationships include remix/edit/instrumental/karaoke and related version
  evidence. They require field-specific interpretation, not generic promotion.
- MusicBrainz does not provide lyrics text, explicitness, audio features, or
  artwork bytes. It is not a defensible edition-label authority where the
  edition designation is absent or only inferred from title/format.

### Gaps

- Current fixture has no release group, status, full date, recordings, ISRC,
  Work/ISWC, artist credits, aliases, or relationships.
- No contract tests cover multiple ISRCs/Works, relationship scope/attributes,
  partial dates, pseudo-releases/transliterations, or the 25-linked-entity
  boundary.
- Current includes are broader than current output but still insufficient for
  complete V3 credit traversal. Wave 1/2 should compute one include union from
  requested fields and reuse each entity response.

Official references: [API](https://musicbrainz.org/doc/MusicBrainz_API),
[rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting),
[release-group types](https://musicbrainz.org/doc/Release_Group/Type),
[artist credits](https://musicbrainz.org/doc/Artist_Credits),
[relationships](https://musicbrainz.org/doc/Relationships),
[artist-recording](https://musicbrainz.org/relationships/artist-recording), and
[recording-work](https://musicbrainz.org/relationships/recording-work).

## MusicBrainz semantic enrichment

- **Files:** `providers/musicbrainz_semantic.py`, `semantic_enrichment.py`,
  `semantic_resolution.py`, genre/semantic classifiers, and
  `tests/test_musicbrainz_semantic.py`.
- **Scopes:** exact Release, Recording/Track, and Artist MBIDs; Work and Area are
  supporting entities, not current mutation scopes.
- **Methods:** release lookup as above; recording with genres/tags,
  artist-credits and Work relationships; exact Work lookup; artist and area
  HTTP lookups for genres/tags/geography.
- **Extracted:** native genres, classified community tags, Work lyric languages,
  artist area/begin-area fallback, area type/ISO country/ancestry.
- **Ignored:** recording artist credits, ISRCs, Work ISWCs/title/type/credits,
  all relationships except recording-to-Work and area `part of`, aliases and
  recording dates. Work `instrumental`/`no lyrics` suppresses language but does
  not emit instrumental state.
- **Confidence/resolution:** native structural evidence uses 0.99; community
  tags use 0.85 and pass taxonomy/noise classification. Genre and semantic
  resolvers preserve scope, structured Discogs style authority, corroboration,
  and lazy Track -> Release -> Artist fallback.
- **Operations:** shared command cache deduplicates exact release, recording,
  Work, artist and area payloads. Supporting entity failures remove only the
  affected evidence. Disabled fields avoid Work traversal.
- **V3 eligible:** genres/styles/moods, Work lyric-language evidence, artist
  geography, and, after schema expansion, Work identity/ISWC, scoped credits,
  relationship-backed version and instrumental evidence.
- **Ineligible:** plain/synced lyrics, explicitness, artwork, audio features,
  and automatic primary artist/title replacement.

The specialized semantic/genre resolvers are a successful V2 boundary and
should remain specialized in V3.

## MusicBrainz identity subsystem

- **Files:** `identity/musicbrainz.py`, `identity/assignment.py`,
  `identity/scoring.py`, `identity/audit.py`, importer/library application and
  tag-sync modules; ADRs 0020-0023 and specs 024-027.
- **Scope:** exactly release, release-group, recording, and release-track MBIDs.
- **Acquisition:** existing release IDs are fetched first; otherwise album
  artist/title search, with singleton track query fallback, at most ten
  candidates, followed by complete release hydration.
- **Matching:** global title/duration/artist/position assignment. Album score
  components are artist 20, album title 20, count 15, titles 25, durations 10,
  order 10, renormalized when unavailable. Existing IDs are acquisition hints
  and comparison state, never positive score.
- **Thresholds:** default album total 90/margin 5/pair 75; singleton total
  95/margin 8. Complete, unambiguous assignment is required by default.
- **Failure:** source failures are explicit; weak, incomplete, tied, or
  insufficient-margin candidates are not repair-ready.
- **Operations:** beets owns transport/pacing. Up to ten hydrated releases can
  be acquired. No cross-subsystem cache reuse with ordinary enrichment is
  demonstrated.
- **V3 boundary:** retain unchanged conceptually. ISRC/Work enrichment may use
  established recording identity but must not enter the four-MBID score.
  Provider agreement, lyrics and artwork remain ineligible for identity.

## Discogs

- **Files:** `providers/discogs.py`, `tests/test_discogs_provider.py`, fixtures
  under `tests/fixtures/discogs/`; ADR 0002 and spec 003.
- **Scope/identity:** one edition-like Discogs Release, by explicit numeric ID
  or conservative search. A Master is not an edition fact source.
- **Methods:** `client.release(id)` plus refresh; otherwise one release search
  page limited to ten artist/title candidates with optional year/barcode/catno,
  followed by concrete release fetch.
- **Extracted:** release ID/URL, genres, ordered styles, label/catno, Barcode
  identifiers, country, positive year, format names and descriptions.
- **Ignored:** format quantity and free text; non-Barcode identifiers; full
  partial release date; release/track credits and `extraartists`; tracklist;
  notes; companies; master linkage; and images.
- **Match/confidence:** normalized exact artist/title; reject known year,
  barcode, or catalog conflicts. Direct 0.98, unique strengthened search 0.92,
  sole weak match 0.82; ambiguity yields no candidates.
- **Failure:** missing/ambiguous/mismatched results give no evidence; transport
  and client failures become sanitized errors. Search requires a token.
- **Operations:** connect/read timeout 5/10 s; dependency-owned backoff; no
  Noqlen cache or retry policy. Official moving-window limits are currently 60
  requests/min authenticated and 25 unauthenticated, exposed in headers.
- **Response reuse:** one full Release response can serve release facts,
  formats, identifiers, artwork metadata, and release/track credit collection.
  Avoid separate calls for each field.

### V3 role and limits

- Strong candidate for edition-like release facts, physical/digital format
  name, quantity, controlled descriptions and free-text differentiator; full
  partial release date; label/catalog/barcode/country; and scoped credits.
- `extraartists` may be release-level, track-level, or restricted by its
  `tracks` text. Blank scope is not proof that a credit applies to every track.
  Roles are semi-structured and may contain comma/bracket detail.
- `identifiers` include matrix/runout, SID codes, pressing plant, rights
  society, ASIN and sometimes ISRC. Discogs ISRC remains release-array text with
  a track description, so it is secondary/corroborating only after unambiguous
  track-position mapping; MusicBrainz recording identity remains primary.
- `images` expose only `primary`/`secondary`, dimensions and signed URLs.
  `primary` is not structurally Front and `secondary` is not Back. Images also
  require authentication. Discogs is therefore ineligible as typed back/disc
  artwork authority without stronger type evidence.
- Free text can support an edition proposal only under conservative controlled
  normalization. It cannot safely manufacture release status, track version,
  or recording date.
- No defensible role for Work/ISWC, vocal language, explicitness, lyrics, audio
  features, or MusicBrainz identity repair.

Official references: [Release API and limits](https://www.discogs.com/developers/),
[credits](https://support.discogs.com/hc/en-us/articles/360005006834-Database-Guidelines-10-Credits),
[formats](https://support.discogs.com/hc/en-us/articles/360005006654-Database-Guidelines-6-Format),
[identifiers](https://support.discogs.com/hc/en-us/articles/360005054893-Database-Guidelines-5-Barcodes-Identifiers),
and [dates](https://support.discogs.com/hc/en-us/articles/360005055093-Database-Guidelines-8-Release-Date).

## Last.fm

- **Files:** `providers/lastfm.py`, semantic classifiers/resolver,
  `tests/test_lastfm_provider.py`, and one album top-tags fixture; ADR 0014 and
  spec 018.
- **Scopes/methods:** `album.getTopTags`, `track.getTopTags`, and
  `artist.getTopTags` against the exact context name or unique MBID, with
  `autocorrect=0`.
- **Extracted:** tag name/count and response identity. URL, popularity and other
  non-tag data are ignored. Only recognized genre/style/mood evidence survives
  deterministic taxonomy/noise classification.
- **Match/confidence:** trim/whitespace/case identity agreement; no fuzzy search
  or autocorrect; community confidence 0.85.
- **Failure:** missing resource codes 6/7 mean no evidence; other API and schema
  errors fail locally.
- **Operations:** 10 s timeout, 1 MiB response cap, at least one second between
  starts per transport, and per-instance release/track/artist caches. No retry
  or `Retry-After`; multiple instances can weaken aggregate pacing. Error 29 is
  rate limiting. Public terms expose no numeric request rate, impose a 100 MB
  reasonable-usage cap, and require suitable caching/attribution.
- **Redundancy:** Track -> Release -> Artist fallback is field-aware and stops
  when requested semantics resolve. Keep this behavior; avoid all-three calls
  by default.
- **V3 role:** secondary/fallback/corroborating classified genre/style/mood
  evidence only. Counts are not comparable across entity methods and are not a
  universal popularity measure.
- **Ineligible:** identity, catalog/date/edition, language, credits,
  explicitness, lyrics, artwork, and audio features. V3 gains no defensible new
  field from Last.fm.

Official references: [artist](https://www.last.fm/api/show/artist.getTopTags),
[album](https://www.last.fm/api/show/album.getTopTags),
[track](https://www.last.fm/api/show/track.getTopTags), and
[terms](https://www.last.fm/api/tos).

## iTunes Search API

- **Files:** `providers/itunes.py`, `tests/test_itunes_provider.py`, and
  `tests/fixtures/itunes/lookup_collection.json`; spec 007.
- **Scope/methods:** Release/collection. Direct collection lookup, UPC lookup,
  then text search limited to ten album results in a configured storefront.
- **Extracted:** collection ID, artist/collection names, release year,
  primary genre and collection URL. Output is only genre/year.
- **Ignored:** full release date, collection/track explicitness, artwork URLs,
  artist/track IDs, UPC, country, track/disc counts, durations, kind, price and
  other digital fields.
- **Match/confidence:** collection type plus normalized artist/title and
  non-conflicting year; direct 0.98, UPC 0.94, text search 0.82. Multiple
  matches yield no evidence.
- **Failure:** malformed/ambiguous direct identity stops; UPC no-match may fall
  through to search; transport/JSON/schema failure is sanitized.
- **Operations:** 10 s timeout, 1 MiB cap, no cache/pacing/retry/429 handling.
  Apple documents an approximate 20 calls/minute and asks large clients to
  cache. Storefront changes catalog shape.
- **Response reuse:** one full album lookup can provide date, album-level
  explicitness, genre, IDs, artwork URLs and digital structure. Track-level
  explicitness requires track rows/entity use, not album propagation.
- **V3 role:** fallback current edition date when present, fallback track and
  release-summary explicitness, fallback front artwork metadata, and
  provider-local IDs/matching evidence. Existing implementation must preserve
  exact date rather than year only.
- **Caveats:** Apple's current result-key table documents
  `collectionExplicitness`/`trackExplicitness` (`explicit`, `cleaned`,
  `notExplicit`), artwork 60/100, IDs and digital fields, but does not list
  `releaseDate` despite its common response presence. Treat it as optional and
  underdocumented. Artwork/promotional content has use restrictions.
- **Ineligible:** original/recording date, physical edition facts, Work/ISWC,
  structured credits, language, lyrics, back/disc art, audio features, and
  identity repair.

Official reference: [Apple Search API](https://performance-partners.apple.com/search-api).

## LRCLIB

- **Files:** `providers/lrclib.py`, `tests/test_lrclib_provider.py`, fixture
  `tests/fixtures/lrclib/get_lyrics.json`; ADR 0016 and specs 020/022.
- **Scope/method:** Track. Exact `/api/get` with track, artist, album and
  duration. The service also has ID and search routes, but current adapter does
  not use them.
- **Extracted:** positive ID, track/artist/album, duration, strict instrumental
  boolean, `plainLyrics`, and `syncedLyrics`. Current instrumental true emits no
  candidate rather than instrumental metadata.
- **Match/confidence:** current client requires trim/whitespace/case identity
  agreement and inclusive +/-2 second duration; fixed confidence 0.95. The
  service itself performs stronger punctuation/diacritic normalization and, if
  multiple exact rows match, selects the lowest ID. There is no identity score.
- **Failure:** missing album/duration avoids I/O; 404 is definitive absence;
  malformed/mismatched/oversized/transport/rate-limit outcomes are distinct
  sanitized errors.
- **Operations:** 10 s, 2 MiB cap, 0.3 s pacing, sequential transport,
  `Retry-After` barrier after 429 without automatic retry, and instance cache of
  success/404 signatures. Importer reuse avoids one instance per track.
- **V3 role:** primary plain and synchronized lyrics source; duration is match
  evidence; instrumental true is eligible corroborating evidence for the
  tri-state only after the field model exists. Plain and synced forms can be
  reused from one response.
- **Wrong-version risk:** there is no MBID/ISRC/version input. Require exact
  established track context, album, duration and version-aware title evidence;
  materially plausible conflicts remain REVIEW. Search should be discovery,
  not an authority shortcut.
- **Ineligible:** lyric/vocal language without separate analysis, explicitness,
  identity, catalog, credits, artwork and audio features.
- **Persistence gap:** plain lyrics have a native target; synchronized lyrics
  are correctly blocked today and require verified `.lrc` sidecar support.

Provider-maintained source:
[routes](https://github.com/tranxuanthang/lrclib/blob/main/server/src/router.rs)
and [metadata lookup](https://github.com/tranxuanthang/lrclib/blob/main/server/src/routes/get_lyrics_by_metadata.rs).

## Cover Art Archive

- **Files:** `providers/coverartarchive.py`, `artwork.py`,
  `artwork_application.py`, and artwork tests. CAA is deliberately outside the
  generic candidate/spec registry.
- **Scope/method:** exact Release JSON; Release Group JSON only after definitive
  exact absence or no eligible exact front.
- **Extracted:** payload release identity; first approved Front; image ID,
  original URL, 1200/500/250 thumbnails and extension/MIME hint.
- **Ignored:** Back, Medium/disc and all other `types`, comments, dimensions and
  additional eligible images.
- **Matching/confidence:** exact release URL must match requested MBID. Artwork
  has typed outcome states rather than generic confidence and never improves
  identity.
- **Failure:** 404 is absence; other HTTP/schema failures are unavailable.
  Release-group fallback does not mask exact-release unavailability.
- **Operations:** `(5, 15)` timeout, at most two metadata calls, no metadata
  response cap/cache/pacing/retry/429 handling. Image download has separate
  bounded validation. CAA publishes no current numeric CAA-specific rate limit
  but defines 503; this is not unlimited authority.
- **V3 role:** primary approved Front and Back for exact Release. `Medium` can
  support disc artwork conditionally, but CAA JSON has no structured disc
  position; multidisc association cannot be guessed from order/comment/image.
  Release-group artwork always retains source-release provenance.
- **Thumbnails:** 250, 500 and 1200 are current keys; `small`/`large` are
  deprecated aliases. Original should not be replaced by a thumbnail unless
  format or configured size requires it.
- **Ineligible:** edition/catalog/semantic evidence, identity score, aesthetic
  ranking, and arbitrary promotion of `secondary` imagery to Back.
- **Test gaps:** no response fixture; no Back/Medium selection, multiple approved
  candidates, dimensions, 307/503, or per-disc ambiguity tests.

Official references: [CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)
and [types](https://musicbrainz.org/doc/Cover_Art/Types).

## AcoustID identity evidence

- **Files:** `acoustid/` subsystem, `identity/acoustid_compatibility.py`, tests in
  `tests/acoustid/`, ADR 0025 and frozen spec 029 contracts.
- **Boundary verdict:** V2 boundary remains correct for V3. Do not register it
  in `ProviderSpec`, ordinary acquisition, or generic field authority.
- **Reuse/generation:** valid existing fingerprint is reused first. Missing
  material invokes bounded `fpcalc -json -length 120` only under explicit
  authority and retains a no-follow source snapshot.
- **Lookup:** bounded HTTPS POST `/v2/lookup`, rounded duration, fingerprint,
  `meta=recordingids`, format JSON. Retains only AcoustID UUID, score and
  recording MBIDs; release/release-group/medium/release-track data is ignored.
- **Evidence:** score >=0.90 and margin >=0.05 by default; support per recording
  is the maximum result-group score, not accumulated votes. Tied/insufficient
  margin is ambiguous.
- **Identity integration:** decisive recording evidence filters already
  structurally eligible MusicBrainz candidates. It adds no score and cannot
  rescue weak, incomplete or ambiguous assignment. It never writes MBIDs.
- **Failure:** unavailable/no-match/ambiguous is neutral for identity. Standalone
  apply may write only `acoustid_id` and `acoustid_fingerprint` to the beets DB;
  never audio files.
- **Operations:** default 15 s, official maximum three requests/second, bounded
  results/recordings/bytes, sequential pacing and process cache up to 256.
  Cache key is digest-based; no raw fingerprint/response is persisted. No retry
  or `Retry-After` behavior.
- **Redundancy:** backend discovery is skipped when all fingerprints exist;
  lookup can be disabled; cache prevents repeated fingerprint+duration calls.
- **Gaps:** no sanitized real-response fixture for schema drift, although strict
  synthetic contract coverage is extensive. Add one only if future parser
  changes make real shape regression value material.
- **Ineligible:** all ordinary metadata, direct MBID write, release selection,
  textual matching, positive structural score, and file-write authority.

Official references: [web service](https://acoustid.org/webservice) and
[FAQ](https://acoustid.org/faq).

## Audit conclusions for Wave 0B

1. Preserve the separate identity, AcoustID, semantic, artwork, and audio
   domains.
2. Add richer evidence/schema contracts before adding V3 fields; do not expand
   adapters into untyped dictionaries.
3. Make acquisition planning union includes and reuse one entity response.
4. Add field/scope/provider roles as a testable artifact rather than encoding
   all policy in ordered tuples.
5. Keep live checks opt-in. Add sanitized fixtures only alongside concrete V3
   parsers where they protect schema/normalization behavior.
