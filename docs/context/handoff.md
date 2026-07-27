# Handoff

## State

Block 020 adds LRCLIB as the first real track-scoped provider while stopping before track execution,
mapping, or application. Existing Discogs, MusicBrainz, Last.fm, and iTunes behavior remains
release-scoped.

## Completed

- Registered disabled-by-default LRCLIB capability for exactly lyrics and synchronized lyrics in the
  immutable track registry.
- Added exact HTTPS `/api/get` transport with selected identity, safe versioned User-Agent, timeout,
  bounded reads, pacing, and Retry-After barriers.
- Added conservative record ID, identity, duration, instrumental, and lyric-shape validation.
- Added provider-local successful/404 caching and independent ordered candidates at confidence 0.95.
- Added synthetic fixture-backed tests, shared resolver/ChangePlan proof, release execution isolation,
  and an opt-in one-request live smoke.
- Documented the no-search, no-logging, and deferred track-execution boundary in ADR 0016.

## Important decisions

- LRCLIB enriches only the exact track selected by beets and never searches or rematches.
- Album title and duration are mandatory for a request; 404 and instrumental are normal no-data.
- Existing Field Authority and canonical planning remain shared and unchanged.
- LRCLIB is track-registry only, so current release importer and CLI never execute it.
- No track mapping, mutation, persistence, or file behavior exists yet.

## Deferred

- Importer precedence among existing Item values, selected TrackInfo values, and `from_scratch`.
- A first read-only/user-visible track planning path.
- Track target mapping/application and persistent/file write policy after that boundary is reviewed.
- Fingerprint generation, network identity lookup, cache, concurrency, and track CLI modes.

## Recommended next block

Stop for independent Block 020 review. Block 021 should decide track current-state composition and
establish a first read-only/user-visible planning path before any TrackInfo or Item application.
