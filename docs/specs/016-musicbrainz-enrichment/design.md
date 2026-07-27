# Design - Anchored MusicBrainz Release Enrichment

## Flow

```text
beets-selected release
  -> validated musicbrainz.release MBID
  -> MusicBrainzAPI.get_release(MBID, includes=[labels, media])
  -> response ID validation
  -> six-field MetadataCandidate tuple
  -> existing resolver and ChangePlan
```

The provider does no search. Missing, malformed, or conflicting MBIDs return an empty tuple before
I/O. A narrow injectable fetch callable backs fixture tests; production lazily constructs beets'
rate-limited client only for a valid direct lookup.

`MusicBrainzProvider` consumes the normalized mapping returned by beets `MusicBrainzAPI`. The beets
boundary has already converted hyphenated raw MusicBrainz HTTP keys such as `label-info` and
`catalog-number` to `label_info` and `catalog_number`; the provider does not support the raw HTTP
shape as a parallel contract.

Normalization trims only strings, stable-deduplicates label/catalog/media tuples, keeps the release
barcode singular within a tuple, and extracts a valid leading year from MusicBrainz partial release
dates. Every candidate uses confidence `0.99`, the canonical MBID, and the public release URL.
Malformed nested values are omitted individually. Invalid or mismatched top-level release identity
raises `ProviderError`.
