# Upgrade to Noqlen Meta 3.0

Noqlen Meta 3.0 preserves the V2 defaults: upgrading does **not**
automatically enable new recording fields, local Key, audio proxies,
synchronized lyrics, or back artwork.

## 1. Upgrade safely

Install the current package **in the same environment as beets**.
These commands suit an ordinary pip/virtualenv setup; if beets was installed
with `uv tool` or `pipx`, use the
[matching installation instructions](../start-here/installation.md) instead:

```bash
pip install --upgrade beets-noqlenmeta
beet nm --help
beet config -p
```

For Key, Energy, or Danceability analysis, install the optional backend:

```bash
pip install --upgrade "beets-noqlenmeta[audio]"
```

Back up the beets library database and your music files before broad
`--apply` runs. Start with a targeted **preview**, not `--all`.

## 2. Choose specific V3 metadata

These are **examples**, not replacement blocks for an entire existing config.
Keep the fields and providers you already configured. For metadata sourced
from MusicBrainz, iTunes and LRCLIB:

```yaml
noqlenmeta:
  fields:
    vocal_languages: true
    instrumental: true
    explicitness: true
    alternate_titles: true
    transliterations: true
    track_version: true
    synced_lyrics: true
    back_artwork: true
  providers:
    musicbrainz:
      enabled: true
    itunes:
      enabled: true
      storefront: us
    lrclib:
      enabled: true
    coverartarchive:
      enabled: true
```

Remember:

- Vocal languages come from verified, unambiguous MusicBrainz
  **Recording-to-Work** links, not from an audio-language detector.
- Instrumental and explicit/clean values require positive source evidence;
  missing evidence is **unknown**, not false or clean.
- Alternate titles and transliterations are structured records, not a
  command to replace the main track title.
- `synced_lyrics` creates a verified no-clobber **`.lrc` sidecar** in the
  existing-library workflow. It does not write universal ID3 SYLT tags.
- `back_artwork` creates an exact-release **`back.jpg`** sidecar when
  eligible. It does not identify printed images on individual CDs.

Only source-authoritative values should be accepted; an ambiguous match can
correctly produce REVIEW or no change.

## 3. Optional local Key, Energy and Danceability

The two audio-analysis permissions below are separate from the field switches:

```yaml
noqlenmeta:
  fields:
    key: true
    energy: true
    danceability: true
  local_analysis:
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
    audio_features:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

**Key** writes to the native beets `initial_key` target only with sufficient
harmonic evidence; an existing key is preserved.

**Energy** is a 0–1 RMS amplitude index (`rms-dbfs-v1`).
**Danceability** is a 0–1 beat/onset regularity index
(`beat-onset-regularity-v1`). These values are **not** calibrated
human-perceptual energy or dance ratings, and not interchangeable with Spotify
scores. Missing measurements stay absent; `0.0` is valid when measured.

Energy, Danceability and their method names are stored **only in the beets
database**, even when `--write` is requested. Other enabled, independently
eligible metadata may still be written to file tags on `--write`.

For other analysis modes, see [BPM, Key and Audio Analysis](../configuration/bpm.md).

## 4. Preview and apply deliberately

```bash
# Preview one selected track (read-only)
beet nm title:"Example Track"

# Preview one album (read-only)
beet nm album:"Example Album"

# Apply approved metadata/sidecars to the beets library
beet nm --apply album:"Example Album"

# Only if you also want eligible, supported audio file tags changed
beet nm --apply --write album:"Example Album"
```

The normal importer has its own `noqlenmeta.preview`,
`noqlenmeta.apply`, and `noqlenmeta.apply_mode` settings. These are
independent of CLI flags that operate on the existing library.

For database/file boundaries, consult
[Database vs File Tags](../advanced/database-vs-file-tags.md)
and the [Field Reference](../technical-reference/fields.md).

## 5. Compatibility and release notes

V3 was tested with Python 3.10–3.14 and beets 2.12 through supported 2.x
releases. Existing V2 beets-library values were preserved by the migration
smoke test. Synthetic FLAC, MP3, M4A, Ogg and Opus files remained byte-identical
for DB-only audio changes in the `--apply --write` regression test.

The public `3.0.0` release does **not** include direct vocal-language recognition
from audio or printed artwork for each disc of a multidisc album.

See the [Release status](../project/release.md) and the
[Changelog](../project/changelog.md).
