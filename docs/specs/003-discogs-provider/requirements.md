# Requirements - Discogs Album Enrichment Provider

## Goal

Implement a production Discogs adapter that conservatively identifies one concrete album release
and emits Block 002 metadata candidates.

## Functional requirements

- Resolve one positive numeric `discogs.release` identifier directly without search.
- Otherwise search one bounded result page with artist/title and available year, barcode, and
  catalog-number filters; search requires a personal user token.
- Select only an exact normalized artist/title match that is unique, or one uniquely strengthened by
  barcode/catalog-number agreement; return no candidates for no match or ambiguity.
- Fetch the selected concrete release before emitting candidates.
- Preserve ordered multi-value genres, styles, labels, catalog numbers, barcodes, media, and format
  descriptions, plus non-empty country and positive year.
- Preserve Discogs genre/style semantics and omit `none` catalog-number placeholders.
- Translate client, service, and network failures to `ProviderError` without credential text.

## Non-goals

Beets lifecycle/configuration, OAuth, resolver/authority behavior, caching, Master Release lookup,
track metadata, writes, and other providers are outside this block.

## Acceptance criteria

Offline fixture-backed tests cover direct lookup, search construction and conservative selection,
normalization/provenance, protocol conformance, and failure translation. Baseline repository
validation passes without a live Discogs request.
