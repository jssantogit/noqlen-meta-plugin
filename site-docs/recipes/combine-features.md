# Combine features without breaking your configuration

Want **synchronized lyrics** and **musical Key** together? You can enable
them in the same beets configuration without enabling everything else.

!!! warning "Edit your existing configuration, don't replace it"
    Run `beet config -p` to find the file and back it up. Preserve other
    plugins, fields, providers and settings you already have. Beets uses
    YAML mappings: writing a second top-level `noqlenmeta:` or `fields:`
    entry can silently replace earlier settings.

## The three places to combine

| What you select | Purpose | Example |
| --- | --- | --- |
| **Fields** | What Noqlen is allowed to enrich | `lyrics: true`, `key: true` |
| **Providers** | Which online catalog is allowed to supply data | `lrclib.enabled: true` |
| **Local analysis** | Which audio-processing task is permitted | `key.enabled: true` |

`fields.key: true` by itself **does not** enable local Key analysis.
Likewise, `fields.lyrics: true` without LRCLIB will not retrieve new lyrics.
These switches **do not authorize writes**; preview and application have
separate permissions.

## 1. Do not paste two separate copies of the same key

This is **incorrect**. The second `noqlenmeta:` can overwrite the first,
depending on the YAML parser:

```text
# WRONG — for illustration only. Never copy this:
noqlenmeta:
  fields:
    lyrics: true
noqlenmeta:
  fields:
    key: true
```

Instead, put both fields under **one `noqlenmeta:`** mapping and merge
the relevant source and local-analysis settings.

## 2. Working combined example

This is a complete small example for someone starting from an empty beets
plugin configuration. If other plugins are installed, **merge**, don't replace
their entries. It enables plain lyrics, time-synchronized `.lrc` sidecars,
and local musical Key estimation.

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  fields:
    lyrics: true
    synced_lyrics: true
    key: true
  providers:
    lrclib:
      enabled: true
  local_analysis:
    key:
      enabled: true
      analysis_mode: window
      window_seconds: 90
```

You can also copy [combined-lyrics-key.yaml](../examples/combined-lyrics-key.yaml).

For Key, first install the optional audio backend:

```bash
pip install "beets-noqlenmeta[audio]"
```

You can later add `fields.energy: true` or `fields.danceability: true`,
but those require the **separate** `local_analysis.audio_features.enabled`
permission and produce database-only signal/rhythm proxies.

## 3. Confirm what beets actually read

After saving the file, inspect the *effective* settings:

```bash
beet config noqlenmeta
```

Look for the `lyrics`, `synced_lyrics` and `key` fields, LRCLIB as an
enabled provider, and `local_analysis.key.enabled: true`.
If any entry is missing, check indentation, duplicate YAML keys, and whether
you edited the file printed by `beet config -p`.

!!! note "A quick reality check"
    Noqlen preserves V2 defaults while V3 optional fields are configured
    explicitly. Not every track will have a lyric match or a confident Key.
    A valid configuration allows the *attempt*; it does not force a result.

## 4. Preview your own track

```bash
beet nm title:"Example Track"
```

Replace `Example Track` with a real track title. The preview can contact
LRCLIB and analyze your audio but doesn't change your library or files.
Use [Read a preview](../start-here/reading-preview.md) to understand what
happened.

When satisfied, `--apply` may persist supported database values and guarded
sidecars; `--apply --write` may also synchronize eligible file tags.
`--write` never turns database-only values into unsupported audio tags.

## More combinations

- [Configuration profiles](configuration-profiles.md): start with one small
  feature set and extend it.
- [Synchronized lyrics](lyrics-synced.md): provider coverage and `.lrc`
  safeguards.
- [Local audio](audio-analysis.md): BPM, Key, Energy and Danceability.
- [Storage destinations](../concepts/data-destinations.md): database versus
  sidecars versus embedded tags.
- [Every configuration option](../technical-reference/configuration.md):
  complete types, defaults and restrictions.
