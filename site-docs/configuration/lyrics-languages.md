# Lyrics & Languages

Plain lyrics and synchronized lyrics are separate fields:

```yaml
fields:
  lyrics: true
  synced_lyrics: false
  lyrics_languages: true
providers:
  lrclib:
    enabled: true
  musicbrainz:
    enabled: true
```

LRCLIB supplies plain and synchronized lyrics for selected tracks and
existing-library Items. Plain lyrics have a writable target. Synchronized
lyrics can be previewed as blocked but are not collapsed into plain lyrics or
written as SYLT because no lossless target is delivered.

MusicBrainz can derive three-letter lyrics-language codes from exact
Recording-to-Work relationships. It also supplies structurally identified
artist countries and areas. `artist_languages` is contextual: it is derived
only from Work languages reached by tracks in the current target, not from an
artist's entire career or guessed from names.

Enable `artist_countries`, `artist_areas`, and `artist_languages` under `fields`
as needed. See the [Fields Reference](../technical-reference/fields.md) for
defaults and targets.
