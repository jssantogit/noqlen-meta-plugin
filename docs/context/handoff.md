# Handoff

## State

Block 004 connects the existing `DiscogsProvider` to beets' selected album phase through
`import_task_choice`. It constructs a provider-independent context and emits a read-only candidate
preview before normal beets metadata application. There is still no resolver, field authority,
candidate application, provenance persistence, or Noqlen metadata write.

## Completed

- Discogs is disabled by default; preview defaults on and the configured personal token is redacted.
- Non-empty `NOQLENMETA_DISCOGS_TOKEN` overrides config; an empty environment value does not erase a
  configured token.
- Album APPLY eligibility excludes SKIP, ASIS, RETAG, TRACKS, ALBUMS, singleton tasks, and missing
  selected `AlbumInfo` values.
- Selected artist/title, year, barcode, catalog number, and defensible Discogs release identity map
  into `ReleaseEnrichmentContext` without mutating `AlbumInfo`.
- Provider failures produce a fixed warning and allow normal import to continue.
- Candidate previews contain only normalized field values and source release identity.
- The optional Discogs client is imported lazily only after an eligible enabled task is selected.
- The provider boundary now catches concrete Discogs, requests, HTTP, and response-decoding failures;
  programming errors propagate.
- An environment-gated production direct-release live smoke test covers public release ID `1`.

## Important decisions

- `import_task_choice` is late enough to observe the selected match and early enough that the preview
  cannot interfere with beets metadata application.
- Explicit `discogs_albumid` values are accepted; generic `album_id` values are accepted only when the
  selected metadata source identifies itself as Discogs. Duplicate release IDs are removed.
- A missing token remains valid for direct release lookup. Tokenless search fails safely at the
  provider boundary and does not abort import.
- Preview-off still permits enrichment but suppresses candidate values at normal output level.

## Deferred

- OAuth, consumer credentials, interactive authentication, and token persistence.
- Resolver, field authority, confidence calibration across providers, candidate application, and
  provenance persistence.
- Caching, Master Release/original-year lookup, track enrichment, cover art, and other providers.
- Before public release/documentation, account for current Discogs API attribution and usage
  requirements; retained public `source_url` values support future provenance and attribution.

## Recommended next block

Block 005 should define the minimum field-authority and resolver policy required to choose between
selected-release metadata and normalized provider candidates. It should preserve candidate
provenance, make overwrite decisions explicit and testable, and establish a review boundary before
any separate metadata-application/write block.
