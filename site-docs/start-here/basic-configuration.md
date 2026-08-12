# Basic Configuration

Add this useful starter configuration below your plugin list:

```yaml
noqlenmeta:
  providers:
    musicbrainz:
      enabled: true
    coverartarchive:
      enabled: true

  fields:
    genres: true
    styles: true
    moods: true
    cover: true

  genres:
    num_genres: 1

  moods:
    max_moods: 1
```

**Providers** are sources of metadata. MusicBrainz and Cover Art Archive need no
API key and are enabled by default.

**Fields** choose the kinds of metadata Noqlen may enrich. This example enables
genres, styles, moods, and album covers.

Feature blocks fine-tune the result. Here, `num_genres` and `max_moods` each set
a maximum of one independently supported value; Noqlen does not invent values
to fill those limits.

You can copy the same configuration from
[`starter-config.yaml`](../examples/starter-config.yaml). Continue with
[Your First Preview](first-preview.md).
