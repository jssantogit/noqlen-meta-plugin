# Design - Discogs Album Enrichment Provider

## Flow

```text
ReleaseEnrichmentContext
        -> direct discogs.release ID, or bounded authenticated search
        -> one defensible release ID
        -> concrete Discogs Release fetch
        -> MetadataCandidate tuple
```

## Resolution

Exactly one valid `discogs.release` value takes the direct path at confidence `0.98`. Malformed,
non-positive, or multiple Discogs release identifiers are ambiguous and return no metadata.

Search sends `type=release`, `artist`, and `release_title`, adding `year`, `barcode`, and `catno` only
when present. It reads at most the first 10 results from page one. Results must match normalized
artist and album title; a conflicting available year excludes a result. Exactly one barcode or
catalog-number match wins at confidence `0.92`. Otherwise exactly one remaining artist/title/year
match is accepted at `0.82`. Multiple strong or remaining matches return no metadata. Confidence is
provider-local release-selection confidence, not field authority.

No relaxation search is currently needed; a constrained no-match returns no candidates.

## Client boundary

`python3-discogs-client` performs production I/O with its normal backoff enabled and connect/read
timeouts of 5/10 seconds. Direct lookup can use an unauthenticated client. Search explicitly requires
a personal user token. Boundary failures use fixed `ProviderError` messages and suppress raw client
exception chaining so request details and credentials cannot escape.

## Normalization

Normalization reads only the fetched release payload. Every candidate uses provider `discogs`, the
concrete release ID, and its public `uri` when present. Ordered unique values are emitted for
`genres`, `styles`, `labels`, `catalog_numbers`, `barcodes`, `media`, and `format_descriptions`.
`country` and `year` are scalar candidates. Only identifiers whose type is `Barcode` become
barcodes, and catalog number `none` is ignored case-insensitively.
