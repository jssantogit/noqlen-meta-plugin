# Analyze BPM, Key, Energy and Danceability

**Goal:** calculate supported attributes from audio files already in your
beets library. No external analysis provider is needed; Noqlen uses its
optional local Librosa backend.

## Install the optional backend

```bash
pip install "beets-noqlenmeta[audio]"
```

## Enable only the features you want

For all four features, merge this complete example into your existing
beets `config.yaml`:

```yaml
noqlenmeta:
  fields:
    bpm: true
    key: true
    energy: true
    danceability: true
  local_analysis:
    bpm:
      enabled: true
      analysis_mode: window
      window_seconds: 90
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
    audio_features:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

You may disable any of these **field and analyzer** pairs independently.
Enabling `fields.key` alone will not analyze Key. The standalone
[copyable profile](../examples/audio-config.yaml) includes the plugin entry.

## Preview a single track

```bash
beet nm title:"Example Track"
```

Preview can decode audio for authorized analysis but never modifies the
original file. It can abstain if the tempo or harmonic evidence is insufficient.

After reviewing, `beet nm --apply title:"Example Track"` can save supported
values to the beets database. Use `--apply --write` only if you also want
eligible **file tags** synchronized.

## What will actually be saved?

| Result | What it means | Storage |
| --- | --- | --- |
| BPM | Estimated tempo; existing values preserved by default | Native BPM, with supported file mapping |
| Key | Conservative pitch-class/harmonic estimate, e.g. `Am` | Native `initial_key`, only when safe |
| Energy | 0–1 RMS intensity proxy (`rms-dbfs-v1`) | beets Item database only |
| Danceability | 0–1 beat/onset regularity proxy (`beat-onset-regularity-v1`) | beets Item database only |

!!! warning "Not perceptual scores"
    Energy is **not** how energetic a listener finds the track.
    Danceability is **not** a Spotify or machine-learned human dance score.
    They are explicitly versioned, reproducible signal proxies. `0.0` can
    be a valid measured value; missing results remain absent.

`--write` will **not** invent media tags for the database-only proxies.
For tuning analysis windows and BPM persistence, see
[BPM & local audio settings](../configuration/bpm.md),
[Data destinations](../concepts/data-destinations.md) and the
[full configuration reference](../technical-reference/configuration.md).
