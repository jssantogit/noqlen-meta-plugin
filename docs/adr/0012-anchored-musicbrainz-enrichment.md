# ADR 0012: Add anchored MusicBrainz release enrichment

- Status: Accepted
- Date: 2026-07-27

## Context

Field Authority already assigns MusicBrainz a role in edition metadata and makes it the highest
authority for release year, but no adapter currently activates that policy. Beets already identifies
MusicBrainz releases and its supported `MusicBrainzAPI` owns MusicBrainz host configuration,
User-Agent behavior, timeouts, retries, and service-specific rate limiting.

## Decision

1. MusicBrainz is an enrichment provider, not a matcher.
2. Enrichment requires one exact validated `musicbrainz.release` MBID.
3. Missing, malformed, or conflicting MBIDs produce no candidates and no network search.
4. No artist/title, barcode, catalog-number, release-group, or fuzzy lookup is performed.
5. Selected `AlbumInfo` and persistent `Album` adapters expose validated canonical release MBIDs
   through `ExternalIdentifier`; Discogs and MusicBrainz IDs may coexist.
6. Production lookup uses the supported beets `MusicBrainzAPI`; Noqlen introduces no second
   MusicBrainz HTTP or rate-limit implementation.
7. Lookup passes explicit narrow includes for `labels` and `media`, rather than the client's broad
   defaults.
8. Current output is limited to labels, catalog numbers, barcodes, country, year, and media.
9. Year comes from the exact release's date. Release-group first release date is not used.
10. Multiple labels, catalog numbers, and media formats remain structured and stable-deduplicated.
11. Existing Field Authority is unchanged. MusicBrainz therefore has highest authority for year,
    while Discogs remains ahead for labels, catalog numbers, barcodes, country, and media.
12. The provider is disabled by default and stores no MusicBrainz credentials or copied beets
    MusicBrainz settings.
13. Expected request failures become fixed, non-sensitive `ProviderError` failures. Internal
    candidate contract failures remain visible.
14. Importer and library mapping, strict/partial application, stale/dirty guards, persistence, and
    file-write semantics do not change.
15. Default tests are fixture-backed and offline. Live validation is opt-in.

## Consequences

Beets remains solely responsible for deciding which release the user has. Noqlen can use the exact
selected edition to activate existing per-field authority without adding matching ambiguity or a
parallel MusicBrainz transport. Structured provider output may expose existing singular-target
mapping blockers, which is intentional and handled by current application policy.
