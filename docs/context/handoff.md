# Handoff

## State

Block 018 adds Last.fm as the fourth built-in provider through the existing shared planning path. It
is disabled by default and declares only `genres` capability.

## Completed

- Verified supported beets exposes `beets.plugins.LASTFM_KEY` and packaged LastGenre `genres.txt`.
- Added direct selected-album `album.getTopTags` enrichment with `autocorrect=0` and no search.
- Added strict response identity, weight, vocabulary, stable deduplication, and three-genre limits.
- Added fixed-confidence structured provenance with no API-key exposure.
- Added bounded transport, monotonic one-second pacing, and provider-local same-album caching.
- Added lazy plugin-instance provider retention and existing capability/fail-open orchestration.
- Added deterministic provider, authority, importer, CLI, failure, resource, and opt-in live tests.
- Documented configuration and the conservative community-classification boundary in ADR 0014.

## Important decisions

- Last.fm is an enricher, not a matcher; selected artist/title identity is never fuzzily changed.
- Raw community tags never map directly to genre, style, or mood.
- Current capability is genres only; style and mood classification remain deferred.
- The supported beets key and vocabulary are reused at runtime without copied secrets or taxonomy.
- Existing authority, resolver, mappings, application, persistence, and file behavior are unchanged.

## Deferred

- Explicit reviewed taxonomies for community-derived styles or mood.
- Persistent caching, concurrency, configurable tag thresholds, and additional providers.
- Physical file-tag synchronization.

## Recommended next block

Stop for independent Block 018 audit. After audit, reassess explicit classification taxonomy or a
provider with already typed metadata; do not promote arbitrary Last.fm tags automatically.
