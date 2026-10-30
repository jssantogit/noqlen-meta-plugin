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
lyrics can create an exact `.lrc` sidecar alongside the existing library audio
file on explicit `beet nm --apply`. Existing sidecars are preserved or
reviewed on conflict; they are not collapsed into plain lyrics and no
cross-format SYLT embedding is promised.

MusicBrainz can derive three-letter lyrics-language codes from exact
Recording-to-Work relationships. It also supplies structurally identified
artist countries and areas. `artist_languages` is contextual: it is derived
only from Work languages reached by tracks in the current target, not from an
artist's entire career or guessed from names.

Enable `artist_countries`, `artist_areas`, and `artist_languages` under `fields`
as needed. See the [Fields Reference](../technical-reference/fields.md) for
defaults and targets.


## Vocal languages in V3

Use `noqlenmeta.fields.vocal_languages: true` with MusicBrainz enabled to
derive an ISO-639-3 *Recording-level* set from a single verified Recording→Work
performance relationship. This is distinct from `lyrics_languages` (the Work's
text language), `artist_languages`, and release-title `language`.

The derivation deliberately abstains on instrumental, karaoke, translated,
partial and medley relations, multiple incompatible Works, missing Work
languages or otherwise ambiguous evidence. Existing language sets are not
silently deleted. **This is not audio language recognition**, does not cover all
bilingual tracks and does not write a speculative embedded `LANGUAGE` tag.
Further acoustic corroboration is possible in a later version, but is not
required for the V3.0 conservative scope.
