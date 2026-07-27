# Handoff

## State

Block 019 establishes track identity and provider-input boundaries without adding a track provider or
track execution. Existing Discogs, MusicBrainz, Last.fm, and iTunes behavior remains release-scoped.

## Completed

- Verified concrete beets 2.12 TrackInfo, AlbumInfo, AlbumMatch, TrackMatch, and Item contracts.
- Added immutable strict `TrackEnrichmentContext` and canonical ISRC handling.
- Added read-only TrackInfo, persistent Item, current-value, and selected-match adapters.
- Added safe MusicBrainz source handling, semicolon-only multi-ISRC parsing, and AcoustID IDs while
  excluding fingerprints.
- Split release/track provider protocols and added explicit immutable scope registries.
- Made album importer and CLI availability checks structurally release-scoped.
- Added focused offline domain, adapter, provider-contract, registry, and release-regression tests.
- Documented the boundary and deferred importer current-value precedence in ADR 0015.

## Important decisions

- Release and track identity contexts are distinct, but candidates, authority, resolver, decisions,
  and `ChangePlan` remain shared.
- Generic TrackInfo IDs are provider-specific and become MusicBrainz IDs only for MusicBrainz data.
- Selected beets mappings are reused without rematching; unmatched extras are excluded.
- Item adapters use local values only and explicitly disable Album fallback.
- No track provider, query, mapping, mutation, persistence, or file behavior exists yet.

## Deferred

- Importer precedence among existing Item values, selected TrackInfo values, and `from_scratch`.
- Track target mapping/application and persistent/file write policy.
- Fingerprint generation, network identity lookup, cache, concurrency, and track CLI modes.

## Recommended next block

Stop for independent Block 019 review. Block 020 may add LRCLIB as the first real
`TrackMetadataProvider`; it must not redesign identity, resolution, or planning, and track
application remains a later separately reviewed block.
