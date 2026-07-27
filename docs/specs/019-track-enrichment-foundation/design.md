# Design - Track Enrichment Foundation

## Flow

```text
TrackInfo or Item
  -> TrackEnrichmentContext
  -> future TrackMetadataProvider
  -> MetadataCandidate
  -> shared Field Authority and resolver
  -> shared ChangePlan
  -> stop before target mapping
```

`track_integration.py` is a read-only boundary. Selected provider identity comes from `TrackInfo`,
with explicit parent `AlbumInfo` fallback only for artist/album and matched Item supplementation only
for approved external IDs. Persistent Item adapters use `with_album=False` throughout.

Provider scope is runtime orchestration metadata on `ProviderSpec`; protocol signatures provide the
static/domain distinction. The canonical all-provider registry remains global-policy input, while
release orchestration uses only the release-filtered registry. The track registry is intentionally
empty until a real provider is added.
