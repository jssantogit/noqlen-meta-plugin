# Design - LRCLIB Track Lyrics Provider

## Flow

```text
TrackEnrichmentContext
  -> LRCLIBProvider exact-signature prerequisite check and cache
  -> _LRCLIBTransport paced HTTPS GET /api/get
  -> bounded JSON and conservative response validation
  -> ordered MetadataCandidate values
  -> existing Field Authority and resolver
  -> existing ChangePlan
  -> stop before target mapping
```

The provider owns exact-signature caching and normalization. The transport owns only URL encoding,
client identification, bounded HTTP, pacing, and Retry-After state. Injected fetch and clock seams
keep deterministic tests offline without creating a parallel fake provider.
