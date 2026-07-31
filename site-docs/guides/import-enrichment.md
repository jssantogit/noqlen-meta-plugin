# Enrich During Import

You will let Noqlen enrich metadata only after beets selects an import match,
while leaving final persistence and file writing to beets.

## Preview First

Enable a release provider and keep application disabled:

```yaml
plugins:
  - musicbrainz
  - noqlenmeta

noqlenmeta:
  preview: true
  apply: false
  providers:
    musicbrainz:
      enabled: true
```

Run the normal beets importer. Noqlen runs only for a selected `apply` task.
Skip, use-as-is, abort, duplicate decisions that do not result in apply, and a
quiet-mode skip fallback do not run Noqlen enrichment or identity work.

## Apply Selected Metadata

After previewing representative imports:

```yaml
noqlenmeta:
  preview: true
  apply: true
  apply_mode: strict
```

Noqlen can mutate only the selected `AlbumInfo` and selected `TrackInfo`
objects. It does not store Items or write files directly. beets later applies
the selected metadata, persists the import, and performs at most its normal
single tag write when `import.write` is enabled.

To test database-only import behavior, use beets' own control:

```yaml
import:
  write: false
```

Plain LRCLIB lyrics require `fields.lyrics: true` and
`providers.lrclib.enabled: true`. Synchronized lyrics can be previewed but are
mapping-blocked in v1. See [beets interaction](../reference/beets-interaction.md).
