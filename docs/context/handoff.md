# Handoff

## State

Block 016 adds MusicBrainz as a disabled-by-default enrichment provider anchored exclusively to an
exact release MBID already known by beets. It activates existing Field Authority without changing
matching, mapping, application, persistence, or file behavior.

## Completed

- Added `MUSICBRAINZ_SPEC` for labels, catalog numbers, barcodes, country, year, and media.
- Added canonical UUID validation and deterministic `musicbrainz.release` context identifiers for
  selected `AlbumInfo` and persistent `Album`; Discogs IDs coexist.
- Added one direct `MusicBrainzAPI.get_release` lookup with explicit `labels` and `media` includes.
- Provider and fixture consume the underscore-normalized release mapping returned by beets, including
  `label_info` and `catalog_number`.
- Missing, malformed, or conflicting MBIDs return no candidates before network work.
- Added response-ID integrity, fixed external failure translation, structured normalization,
  confidence, and public provenance.
- Added capability-gated orchestration through the shared provider collection and planning path.
- Added fixture-backed provider and integration coverage plus an opt-in live smoke test.
- Documented configuration and the anchored-provider decision in ADR 0012.

## Important decisions

- MusicBrainz does not match or search for releases.
- Beets' supported MusicBrainz client remains the sole HTTP/rate-limit implementation.
- The provider consumes beets-normalized mappings and does not support raw hyphenated HTTP keys as a
  parallel payload contract.
- Release year uses the exact release date, never release-group first release date.
- Multi-values remain structured and may expose existing singular-target blockers.
- Existing authority remains unchanged: MusicBrainz leads year; Discogs leads its higher-authority
  edition fields.
- No MusicBrainz credentials or copied beets MusicBrainz settings belong to Noqlen configuration.
- Write and file semantics remain exactly as established through Block 015.

## Deferred

- MusicBrainz identity, relationships, credits, recordings, genres/tags, artwork, and search.
- Additional providers such as Last.fm.
- Physical file-tag synchronization and media-to-Item mapping.

## Recommended next block

Stop for independent Block 016 audit before reassessing provider direction. Do not automatically
extend MusicBrainz scope or add physical tag writes.
