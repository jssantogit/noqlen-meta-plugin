# Noqlen Meta

Noqlen Meta is a beets plugin for multi-provider metadata enrichment and
MusicBrainz identity tools. beets remains the matcher and library manager:
Noqlen enriches releases and tracks that beets has already selected, and it
offers separate workflows to audit MusicBrainz identity, use AcoustID as
recording-level identity evidence, and synchronize four confirmed MusicBrainz
IDs to audio-file tags.

Noqlen previews by default. Ordinary database and approved artwork-sidecar
changes require `--apply`; audio-file mutation requires `--write`. Specialized
identity-tag file replacement requires `--identity-tags --write`. There is no
`--force` option.

The current stable release is Noqlen Meta `2.0.0`, published on PyPI and GitHub.

## Capabilities

- Enrich releases, tracks, and artists with semantic genres, styles, moods,
  languages, and geography from Discogs, MusicBrainz, Last.fm, and iTunes.
- Add selected-track plain lyrics from LRCLIB during import.
- Preview or apply ordinary enrichment to albums already in a beets library.
- Synchronize supported ordinary metadata to files through a verified
  `--apply --write` workflow.
- Select and apply verified Cover Art Archive album artwork, including
  deterministic `cover.jpg` sidecars and optional embedding.
- Analyze local BPM with optional lazy Librosa support from the `[audio]` extra.
- Audit and repair release, release-group, recording, and release-track MBIDs.
- Use decisive AcoustID recording evidence to filter incompatible MusicBrainz
  identity candidates without changing structural scores or thresholds.
- Preview or apply standalone existing-library AcoustID evidence, including
  explicit calculation of missing fingerprints when requested.
- Synchronize four coherent database MBIDs to supported audio files.
- Keep provider lookup, database application, fingerprint calculation, and file
  writing separately authorized.

Noqlen does not rematch ordinary enrichment targets. It does not call
Navidrome APIs; Navidrome is a possible consumer of resulting file tags.

## Documentation

The complete manual is available on
[Read the Docs](https://noqlen-meta.readthedocs.io/en/stable/). The
[`site-docs/`](https://github.com/jssantogit/noqlen-meta-plugin/tree/main/site-docs)
source is available for contributions.

Start with:

- [Installation](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/getting-started/installation.md)
- [First safe preview](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/getting-started/first-preview.md)
- [Command reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/commands.md)
- [Configuration reference](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/reference/configuration.md)
- [Troubleshooting](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/site-docs/troubleshooting/index.md)

## Installation

Install Noqlen Meta in the same Python environment as beets:

```bash
pip install beets-noqlenmeta
```

Discogs search needs the optional client:

```bash
pip install "beets-noqlenmeta[discogs]"
```

Opt-in local BPM analysis uses the lazy audio extra:

```bash
pip install "beets-noqlenmeta[audio]"
```

No extra Python dependency is required for AcoustID lookup or stored-fingerprint
reuse. Explicit missing-fingerprint calculation uses an external `fpcalc`
executable (Chromaprint), configurable through `noqlenmeta.acoustid.fpcalc`.

Enable the plugin in the beets `config.yaml`:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  preview: true
```

Run `beet config -p` to print the configuration path. beets chooses the normal
platform-specific configuration directory; do not assume the same path on
Linux, macOS, and Windows.

Verify that the plugin loaded:

```bash
beet help noqlenmeta
```

The command is `beet noqlenmeta`; `beet nm` is the preferred alias.

## First Preview

MusicBrainz is enabled by default and uses only exact MBIDs already known by
beets; it never performs fuzzy identity search:

```yaml
noqlenmeta:
  providers:
    musicbrainz:
      enabled: true
```

Preview one existing album:

```bash
beet nm album:"Example Album"
```
