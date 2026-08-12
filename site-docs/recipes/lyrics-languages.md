# Add Lyrics and Language Metadata

Enable plain lyrics and semantic language fields with their sources:

```yaml
noqlenmeta:
  fields:
    lyrics: true
    synced_lyrics: false
    lyrics_languages: true
    artist_languages: true
    artist_countries: true
    artist_areas: false
  providers:
    lrclib:
      enabled: true
    musicbrainz:
      enabled: true
```

Preview an existing track or album:

```bash
beet nm title:"Example Track"
```

LRCLIB supplies track lyrics. MusicBrainz Work relationships provide
three-letter lyrics-language codes and contextual artist languages; identified
artist areas provide countries and optional main areas.

Synchronized lyrics remain a separate preview/block-only field because no
lossless writable target is delivered. Noqlen never collapses synchronized text
into plain lyrics.
