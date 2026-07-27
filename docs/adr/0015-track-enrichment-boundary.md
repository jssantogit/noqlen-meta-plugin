# ADR 0015: Establish a track enrichment boundary

- Status: Accepted
- Date: 2026-07-27

## Context

Noqlen's current providers enrich selected releases. Future lyrics, fingerprint-derived identity,
and deeper recording enrichment need track identity without duplicating the existing field authority,
resolution, and planning architecture or rematching tracks already selected by beets.

## Decision

1. Release and track enrichment have distinct identity contexts; `ReleaseEnrichmentContext` remains
   the release identity and provider-input boundary.
2. `TrackEnrichmentContext` carries required artist/title, optional album title, duration, track/disc
   numbers, and namespaced external identifiers.
3. `MetadataCandidate`, `FieldRule`, `ResolutionPolicy`, `FieldDecision`, and `ChangePlan` remain
   shared. There is no track-specific resolver, decision, or change plan.
4. Provider protocols are separated into synchronous release and track contracts that emit the same
   `MetadataCandidate` type.
5. `ProviderSpec` declares an explicit release or track scope. The global registry remains the source
   for cross-scope configuration and display concerns, while immutable filtered registries guide
   scope-specific orchestration.
6. Discogs, MusicBrainz, Last.fm, and iTunes remain release-scoped. Release orchestration consults
   only release specs; future track orchestration will consult only track specs.
7. Generic `TrackInfo.track_id` is provider-specific and is interpreted as a MusicBrainz recording
   ID only when `data_source` says MusicBrainz, case-insensitively. The same source guard applies to
   generic `release_track_id`.
8. Explicit `mb_trackid` and `mb_releasetrackid` values are independently UUID-validated regardless
   of the selected provider source.
9. Initial track external identity supports MusicBrainz recording, MusicBrainz release-track, ISRC,
   and AcoustID track IDs. AcoustID fingerprints are intentionally excluded.
10. Multiple ISRCs are parsed only from beets' known semicolon-separated representation. Each
    component is validated and stable-deduplicated; no other heuristic separator is used.
11. The already-selected `AlbumMatch` Item-to-`TrackInfo` mapping is reused without matcher calls.
    `TrackMatch` supplies the singleton boundary, and unmatched extra Items or TrackInfos are excluded.
12. Persistent Item context and current-value reads are read-only, use Item-local values, and disable
    Album fallback to avoid unnecessary relation access.
13. Initial canonical track current values are `lyrics` and `synced_lyrics` only. Selected
    `TrackInfo` and existing Item values are exposed as separate truthful sources.
14. Importer precedence between existing Item current values, selected `TrackInfo` values, and
    `from_scratch` behavior is deferred to the provider/import planning block.
15. This block adds no track provider, target mapping, application, persistence, file write, network
    lookup, or track CLI mode. The album-oriented command and existing release behavior are unchanged.

## Consequences

LRCLIB or another real track provider can consume stable track identity and emit ordinary candidates
without redesigning resolution. A later reviewed block must decide current-state composition and map
canonical track plans to `TrackInfo` or persistent Item targets before any track metadata can change.
