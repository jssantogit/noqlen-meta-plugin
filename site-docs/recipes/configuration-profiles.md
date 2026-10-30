# Choose a configuration profile

**You do not need to enable everything.** Choose the smallest profile
that supports the result you want. Every example is a real beets configuration
fragment, not a replacement for your existing configuration.

Before copying a block, open your config location with `beet config -p`.
Keep **one** `plugins:` list and **one** `noqlenmeta:` block, and merge
only the settings you want. Duplicate YAML keys can silently discard earlier
settings.

## Profile A — Starter library enrichment

Good for genres, styles, moods, and verified front covers. Uses default
no-credential sources MusicBrainz and Cover Art Archive.

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  fields:
    genres: true
    styles: true
    moods: true
    cover: true
  providers:
    musicbrainz:
      enabled: true
    coverartarchive:
      enabled: true
```

[Starter YAML](../examples/starter-config.yaml) includes explicit
one-genre and one-mood limits.

## Profile B — Plain and synchronized lyrics

LRCLIB is opt-in. Synchronized lyrics may create guarded `.lrc` sidecars.

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  fields:
    lyrics: true
    synced_lyrics: true
  providers:
    lrclib:
      enabled: true
```

[Download/copy this YAML](../examples/lyrics-config.yaml) or follow
[the lyrics recipe](lyrics-synced.md).

## Profile C — Detailed Recording and Work credits

Enable specific MusicBrainz-related recording opt-ins to preserve verified
credits and identities without changing the main title or artist:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  fields:
    composers: true
    lyricists: true
    performers: true
    structured_artist_credits: true
    vocal_languages: true
    alternate_titles: true
  providers:
    musicbrainz:
      enabled: true
```

Use [credits-config.yaml](../examples/credits-config.yaml) and
[the Recording recipe](recording-credits.md) for additional fields.

## Profile D — Local audio analysis

First install `pip install "beets-noqlenmeta[audio]"`. This preset
turns on BPM and conservative Key only. Add Energy and Danceability
separately if the proxies are useful.

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  fields:
    bpm: true
    key: true
  local_analysis:
    bpm:
      enabled: true
      analysis_mode: window
      window_seconds: 90
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

See [audio-config.yaml](../examples/audio-config.yaml) for all four
analysis options and [the audio recipe](audio-analysis.md) for limitations.

## Combine two profiles

To add features from two profiles, **merge** their `fields`, `providers`
and `local_analysis` sections inside the same `noqlenmeta:` block.
Do not paste a second `plugins:` or `noqlenmeta:` key.
See the [worked combined lyrics + Key example](combine-features.md).

## Test each profile safely

```bash
beet nm title:"Example Track"
```

Use an album query instead if you want album-scope fields such as artwork:

```bash
beet nm album:"Example Album"
```

Remember: every profile starts with **preview**. Do not add `--apply`
until you've inspected its output.

For every option, its default and the interaction between features, see
[the configuration reference](../technical-reference/configuration.md).
