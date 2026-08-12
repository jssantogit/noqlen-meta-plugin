# Providers And Field Authority

You will understand why enabling a provider does not make it supply every
field, and why the highest-confidence source does not always win.

Three controls intersect:

1. A field must be enabled.
2. A provider must be enabled and currently support that field and target scope.
3. The provider must appear in that field's authority order and meet its confidence threshold.

Field authority is a preference order. After candidates meet the confidence
threshold, the highest-authority available provider wins; a lower-authority
candidate does not win merely because its numeric confidence is higher.

```yaml
noqlenmeta:
  fields:
    genres: true
  providers:
    discogs:
      enabled: true
    lastfm:
      enabled: true
  resolution:
    authority:
      genres: [discogs, lastfm]
```

An authority override replaces the complete built-in order for that field. It
does not enable a provider, grant write permission, or expand a provider's
capabilities. `preserve_existing: false` can turn an existing-value conflict
into a proposal, but still grants no write permission.

MusicBrainz enrichment under `providers.musicbrainz.enabled` is not the
MusicBrainz identity source. Identity audit has separate importer settings and
separate command flags. See the [provider reference](../technical-reference/providers.md)
and [configuration reference](../technical-reference/configuration.md).
