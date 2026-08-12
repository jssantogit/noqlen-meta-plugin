# Noqlen Meta

Noqlen Meta is a beets plugin for multi-provider metadata enrichment and
MusicBrainz identity tools. beets remains the matcher and library manager:
Noqlen enriches releases, tracks, and artists that beets has already selected,
with separate workflows for MusicBrainz identity and AcoustID evidence.

Ordinary enrichment previews by default. Database changes, verified artwork
application, and audio-file synchronization remain explicitly authorized rather
than happening implicitly.

## Capabilities

- Enrich release, track, and artist metadata with genres, styles, moods,
  languages, artist geography, and release details from focused providers.
- Retrieve supported plain lyrics from LRCLIB.
- Enrich importer-selected music and albums or standalone items already managed
  by a beets library.
- Select and apply verified Cover Art Archive artwork, including deterministic
  `cover.jpg` sidecars and optional embedding.
- Analyze local BPM with the optional `[audio]` extra and lazy Librosa support.
- Audit and repair MusicBrainz identity and use AcoustID fingerprints or
  recording evidence in explicit existing-library workflows.
- Synchronize supported ordinary metadata and BPM to audio files through the
  verified write path, with identity-tag synchronization kept separate.

## Installation

Install Noqlen Meta in the same Python environment as beets:

```bash
pip install beets-noqlenmeta
```

Discogs support uses the optional Discogs client:

```bash
pip install "beets-noqlenmeta[discogs]"
```

Optional local BPM analysis uses the audio extra:

```bash
pip install "beets-noqlenmeta[audio]"
```

Enable the plugin in the beets `config.yaml`:

```yaml
plugins:
  - noqlenmeta
```

Verify that beets loaded the plugin:

```bash
beet help noqlenmeta
```

`beet noqlenmeta` is the full command name; `beet nm` is the preferred alias.
