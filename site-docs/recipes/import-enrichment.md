# Enrich During Import

Importer enrichment is a secondary path for users already comfortable with
ordinary previews. beets still chooses the match, persists the import, and
performs its configured final tag write.

```yaml
noqlenmeta:
  preview: true
  apply: false
  apply_mode: strict
  fields:
    genres: true
    styles: true
    moods: true
    lyrics_languages: true
  providers:
    musicbrainz:
      enabled: true
```

Run your normal beets import. Noqlen acts only on a selected `Action.APPLY`
task; skip, use-as-is, and abort decisions do not become Noqlen targets.

Review importer output first. Set `noqlenmeta.apply: true` only when approved
ordinary proposals should mutate the selected AlbumInfo/TrackInfo. beets owns
later database persistence and `import.write` tag behavior. Shipped semantic
fields such as moods, lyrics languages, and artist geography are not deferred;
they apply where production has a lossless selected-metadata target.

Native beets/chroma owns importer acoustic matching and fingerprint submission.
Noqlen's AcoustID feature is an existing-library evidence workflow and does not
replace chroma.

See [beets Interaction](../technical-reference/beets-interaction.md) for exact
import decisions and write boundaries.
