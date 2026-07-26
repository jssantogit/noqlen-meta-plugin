# Design - Metadata Domain and Provider Contract

## Flow

```text
identified beets release
        -> ReleaseEnrichmentContext
        -> MetadataProvider.get_candidates()
        -> MetadataCandidate sequence
        -> future authority/resolver
```

The future beets integration layer will translate selected release data into the domain context.
Neither the context nor provider boundary imports beets.

## Domain model

- `ExternalIdentifier` stores a non-empty namespace and value, allowing identifiers to grow
  without provider-specific context fields.
- `ReleaseEnrichmentContext` is a frozen album-level value containing only practical identity and
  search hints for the first provider slice.
- `MetadataCandidate` is a frozen field proposal. Values are strings, finite integers/floats,
  booleans, or non-empty tuples of non-empty strings.
- Confidence is a finite inclusive `0.0..1.0` value. The endpoints mean no provider confidence and
  full provider confidence; interpretation and authority weighting are deferred to the resolver.
- `provider`, `source_id`, and optional `source_url` preserve the minimum explanation boundary for
  future provenance and review.

## Provider boundary

`MetadataProvider` is a runtime-checkable synchronous `Protocol` with a stable `name` and
`get_candidates(context) -> Sequence[MetadataCandidate]`. Production implementations may use any
private client, but raw client response and exception types are absent from the public contract.
`ProviderError` is the single service-boundary exception.

## Compatibility

The current beets `AlbumInfo` interface supplies artist/title, year, barcode, catalog number, and
external release IDs needed to construct this context later. No beets internals are copied.

## Deferred choices

Field vocabulary, authority/conflict policy, confidence calibration across providers, richer
provenance persistence, track contexts, and the beets mapping/hook remain future blocks.
