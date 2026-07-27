# Design - Importer Track Planning Preview

## Flow

```text
selected AlbumMatch mapping or TrackMatch
  -> TrackEnrichmentContext
  -> beets-parity effective current values
  -> eligible retained LRCLIB provider
  -> validated MetadataCandidate values
  -> existing Field Authority and resolver
  -> existing ChangePlan
  -> sanitized summary preview
  -> stop before track target mapping or application
```

For albums, the selected overlay comes from `TrackInfo.merge_with_album(AlbumInfo)`; for singletons it
comes from `TrackInfo.item_data`. The local baseline is Item-local canonical metadata when
`from_scratch` is false. When true, fields in `Item._media_tag_fields` are removed from that baseline
to mirror `Item.clear()`, flexible fields remain, and selected metadata is overlaid last. Thus current
beets behavior clears omitted `lyrics` but retains omitted `synced_lyrics`.

The normal provider collector supplies sanitized `ProviderError` fail-open and candidate validation;
validation contract errors remain outside that catch and propagate. Release planning runs through its
existing branch and may coexist with track preview. Track rendering exposes identity and plan
metadata, but lyric values are reduced to character and line counts.
