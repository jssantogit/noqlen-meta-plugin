# Fields

Fields choose the kinds of metadata Noqlen may handle:

```yaml
fields:
  genres: true
  styles: true
  moods: true
  bpm: true
  lyrics: false
  cover: true
```

Release and album fields include `genres`, `styles`, `labels`,
`catalog_numbers`, `barcodes`, `country`, `year`, `media`, and
`format_descriptions`. Track fields include `moods`, `bpm`, `lyrics`,
`synced_lyrics`, and `lyrics_languages`. Artist-derived fields are
`artist_countries`, `artist_areas`, and `artist_languages`. `cover` controls
album artwork.

Most fields default on. `lyrics`, `synced_lyrics`, and `artist_areas` default
off. A field switch grants no mutation authority and cannot make an enabled
provider supply a capability it does not have.

Synchronized lyrics can be previewed as blocked but have no lossless writable
target. `local_analysis.mood.enabled` also exists in defaults, but no local mood
model is implemented.

Use the topic pages for setup and the [Fields Reference](../technical-reference/fields.md)
for exact storage targets and limitations.
