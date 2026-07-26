# Design - Beets Lifecycle Preview

## Flow

```text
selected beets AlbumInfo
        -> import_task_choice eligibility
        -> ReleaseEnrichmentContext
        -> DiscogsProvider
        -> MetadataCandidate sequence
        -> safe preview
        -> unchanged beets import
```

## Lifecycle boundary

The listener requires an album task with `Action.APPLY`, a match, and a selected `AlbumInfo`. This
excludes all action constants that do not apply a selected album match, regrouping paths, and
singletons. The listener neither changes `choice_flag` nor participates in candidate matching.

## Identity mapping

Artist and album title are required. Year, barcode, and catalog number are copied when valid. A
positive numeric `discogs_albumid` becomes `discogs.release`; `album_id` is used only when
`data_source` is Discogs. Repeated IDs are removed. The selected `AlbumInfo` is never retained or
mutated.

## Configuration and failure safety

The plugin's Confuse namespace owns defaults and token redaction. Environment token resolution is
performed immediately before lazy provider construction. The provider normalizes expected external
failures into fixed `ProviderError` messages; the listener emits a fixed warning and returns so beets
continues normally. The optional Discogs module is imported only after configuration and task
eligibility checks pass, so loading the disabled plugin does not require the Discogs extra.

## Preview

Only normalized candidate source ID, field names, and scalar or joined tuple values are printed. Raw
payloads, exception text, and credentials are never rendered. Preview-off suppresses normal candidate
output but does not disable enrichment.
