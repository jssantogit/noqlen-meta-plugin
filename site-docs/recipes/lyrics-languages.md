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

Synchronized lyrics are separate from plain text. For an existing-library Item,
`fields.synced_lyrics: true` with LRCLIB can prepare an `.lrc` sidecar and
`beet nm --apply` creates it only when the target is verified and absent.
Conflicting sidecars require review, and no speculative SYLT embedding occurs.

`fields.vocal_languages: true` is a separate V3 opt-in: a single verified
MusicBrainz Recording→Work performance may yield ISO-639-3 vocal languages;
translated, instrumental, multiple-Work or ambiguous links abstain. This is
not direct language recognition from the audio.
