# Handoff

## State

Block 003 adds the first production provider, `DiscogsProvider`, on top of the unchanged Block 002
domain/provider contracts. The package still has no beets configuration/lifecycle integration,
resolver, field authority, persistence, or writes.

## Completed

- Optional `python3-discogs-client>=2.8,<3` runtime extra, also installed by development extras.
- ADR 0002 documenting the maintained client, no hand-written HTTP client, personal token first, and
  the provider boundary.
- Exact direct lookup for one positive numeric `discogs.release` identifier without requiring search
  authentication.
- Personal-token authenticated structured release search, bounded to 10 results on page one.
- Conservative exact normalized artist/title selection, optional year exclusion, and unique
  barcode/catalog-number strengthening.
- Concrete release fetch before normalization and candidate provenance.
- Native Discogs genres/styles; all meaningful labels, catalog numbers, and Barcode identifiers;
  country, year, media, and format descriptions.
- Fixed provider-boundary errors, 5/10 second connect/read timeouts, and normal client backoff.
- Sanitized release/search fixtures and deterministic offline tests of the production adapter.

## Important decisions

- Malformed, non-positive, or multiple `discogs.release` identifiers return no metadata rather than
  falling back to a weaker search.
- Search no-match and ambiguity return `()`; service/client/network failures raise `ProviderError`.
- Confidence is local release-selection confidence: direct `0.98`, uniquely identifier-strengthened
  search `0.92`, and unique artist/title/year search `0.82`. All fields from one release share it.
- No controlled search relaxation is implemented because returning no metadata is safer and keeps
  selection explainable.
- The optional dependency is imported only by the Discogs provider module, not generic contracts.

## Deferred

- Beets configuration and lifecycle wiring, including secure token delivery.
- OAuth, consumer credentials, interactive authentication, and token persistence.
- Resolver, field authority, confidence calibration across providers, and provenance persistence.
- Caching, Master Release/original-year lookup, track enrichment, cover art, and other providers.
- Live API smoke coverage. Default tests remain fixture-backed and offline.
- Before public release/documentation, account for current Discogs API attribution and usage
  requirements; retained public `source_url` values support future provenance and attribution.

## Recommended next block

Block 004 should be the narrow beets configuration and lifecycle integration slice that constructs a
`ReleaseEnrichmentContext`, supplies the Discogs personal token to this provider, and invokes it at a
reviewable album-level point. Keep resolver/field-authority policy and metadata writes out unless
they are separately scoped.
