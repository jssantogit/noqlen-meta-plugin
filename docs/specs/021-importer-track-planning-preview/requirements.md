# Requirements - Importer Track Planning Preview

## Goal

Preview canonical plans for tracks already selected by the importer without adding track writes or
changing release and library-command behavior.

## Requirements

- Plan selected `AlbumMatch` mappings and singleton `TrackMatch`; exclude extras and never rematch.
- Execute LRCLIB only when importer preview is enabled and provider, field, and authority gates make
  it eligible; retain one lazily created provider instance.
- Mirror beets 2.12.x selected metadata: album `TrackInfo.merge_with_album(AlbumInfo)` and singleton
  `TrackInfo.item_data`.
- For `from_scratch: false`, overlay selected metadata on Item-local canonical values. For
  `from_scratch: true`, mirror `Item.clear()` before the selected overlay: clear modeled writable
  media fields while retaining flexible metadata.
- Record current behavior that omitted selected lyrics are cleared while omitted selected
  `synced_lyrics` survive under `from_scratch: true`.
- Reuse existing candidate validation, Field Authority, resolver, and `ChangePlan`.
- Treat `ProviderError` as sanitized per-call fail-open and let contract errors propagate.
- Render decisions using character/line summaries only; never render raw lyrics.
- Permit release and track plans to coexist while preserving all release application behavior.
- Add no track mutation, target mapping, application, database/store call, tag or file write, or
  track mode to the album-only library CLI.

## Deferred

Beets does not model `synced_lyrics` as a standard persistent Item media field. A future application
block must decide its target and persistence semantics.
