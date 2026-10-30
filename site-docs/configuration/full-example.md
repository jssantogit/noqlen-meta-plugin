# Default configuration snapshot

!!! warning "These are defaults, not the full list of available features"
    This file reproduces the *established default configuration* exactly.
    New V3 features such as `key`, `energy`, `danceability`,
    `vocal_languages`, `back_artwork` and `explicitness` are **intentionally
    absent** until you explicitly opt in. Their absence doesn't mean the
    features are unsupported.

**Do not copy this entire file just to get started.** Instead, choose a
small [configuration profile](../recipes/configuration-profiles.md).

The block below exactly matches the production defaults represented by
[`full-config.yaml`](../examples/full-config.yaml):

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  preview: true
  apply: false
  apply_mode: strict

  identity:
    enabled: false
    preview: true
    apply: false

  acoustid:
    enabled: false
    reuse_existing: true
    compute_missing: false
    lookup: true
    use_for_identity: true
    min_score: 0.90
    min_margin: 0.05
    max_results: 5
    max_recordings_per_result: 10
    timeout_seconds: 15.0
    requests_per_second: 3.0
    cache_entries: 256
    fpcalc: fpcalc

  fields:
    genres: true
    styles: true
    labels: true
    catalog_numbers: true
    barcodes: true
    country: true
    date: true
    original_date: true
    release_type: true
    release_secondary_types: true
    release_status: true
    edition: true
    year: true
    media: true
    format_descriptions: true
    moods: true
    bpm: true
    lyrics_languages: true
    artist_countries: true
    artist_areas: false
    artist_languages: true
    lyrics: false
    synced_lyrics: false
    cover: true
    isrcs: true
    works: true
    iswcs: true
    recording_date: true
    composers: true
    lyricists: true
    producers: true
    arrangers: true
    conductors: true
    performers: true
    featured_artists: true
    structured_artist_credits: true

  genres:
    num_genres: 1
    promote_styles: true

  moods:
    max_moods: 1

  providers:
    discogs:
      enabled: false
      user_token: ""
    musicbrainz:
      enabled: true
    lastfm:
      enabled: false
    itunes:
      enabled: false
      storefront: us
    lrclib:
      enabled: false
    coverartarchive:
      enabled: true

  artwork:
    size: original
    replace_existing: false

  bpm:
    round: false
    recalculate_existing: false
    octave_normalization: false
    octave_range:
      min: 70
      max: 180

  resolution:
    authority: {}
    min_confidence: {}
    preserve_existing: {}

  local_analysis:
    bpm:
      enabled: false
      analysis_mode: full
      window_seconds: 90
    mood:
      enabled: false
```


## How to enable a V3 feature

For example, local Key needs *both* a field switch and an analyzer:

```yaml
noqlenmeta:
  fields:
    key: true
  local_analysis:
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

Install the optional `[audio]` extra first.
For all available optional fields, see the
[Field Reference](../technical-reference/fields.md) and
[local audio recipe](../recipes/audio-analysis.md).
