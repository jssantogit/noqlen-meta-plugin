# Noqlen Meta

**Enrich the music you already manage with [beets](https://beets.io/)** — genres,
styles, release details, recording credits, artwork, lyrics, and optional local
audio analysis. Noqlen adds evidence-backed metadata to matches selected by
beets; it does **not** replace beets' matching or library management.

**Nothing in your library changes during a preview.** You decide when to apply
metadata and separately when to synchronize supported tags to audio files.

**[Read the documentation](https://noqlen-meta.readthedocs.io/en/latest/) ·
[Start with one album](https://noqlen-meta.readthedocs.io/en/latest/start-here/quickstart/) ·
[Choose a feature](https://noqlen-meta.readthedocs.io/en/latest/recipes/) ·
[Configuration reference](https://noqlen-meta.readthedocs.io/en/latest/technical-reference/configuration/)**

> The `latest` documentation follows the main branch and includes the newest
> V3 guide. The `stable` documentation follows the newest active release tag;
> these may differ until the next documentation release.

## Quick start

You need Python 3.10–3.14, a supported beets 2.x installation, and at least
one album already in your beets library.

```bash
pip install beets-noqlenmeta
beet config -p
```

In the beets `config.yaml` shown by the second command, add Noqlen to your
existing plugin list (do not create a second `plugins:` key):

```yaml
plugins:
  - noqlenmeta
```

Check that beets loaded it, then preview one album in **your** collection:

```bash
beet help noqlenmeta
beet nm album:"Discovery"
```

Replace `Discovery` with an album you actually have. This last command only
**previews** proposed changes. Inspect `KEEP`, `PROPOSE`, `REVIEW`, and
`BLOCKED` results before applying anything.

```bash
# Only after inspecting a preview:
beet nm --apply album:"Discovery"

# Optional: also write supported metadata into the audio files:
beet nm --apply --write album:"Discovery"
```

The database, audio tags, and `cover.jpg` / `.lrc` / `back.jpg` sidecar files
are different destinations with different safety rules. See
[what each command changes](https://noqlen-meta.readthedocs.io/en/latest/concepts/data-destinations/).

## What can I customize?

| I want to... | Start here |
| --- | --- |
| Add genres, styles, moods or release details | [Configuration basics](https://noqlen-meta.readthedocs.io/en/latest/configuration/) |
| Add covers or back artwork | [Artwork recipe](https://noqlen-meta.readthedocs.io/en/latest/recipes/artwork/) |
| Add plain or synchronized lyrics | [Lyrics recipe](https://noqlen-meta.readthedocs.io/en/latest/recipes/lyrics-synced/) |
| Add Recording/Work credits and version details | [Recording metadata recipe](https://noqlen-meta.readthedocs.io/en/latest/recipes/recording-credits/) |
| Calculate BPM, Key, Energy or Danceability | [Audio analysis recipe](https://noqlen-meta.readthedocs.io/en/latest/recipes/audio-analysis/) |
| Repair MusicBrainz IDs | [Identity recipe](https://noqlen-meta.readthedocs.io/en/latest/recipes/repair-musicbrainz-ids/) |
| Understand every field/provider | [Technical reference](https://noqlen-meta.readthedocs.io/en/latest/technical-reference/) |

New V3 features are optional; your existing V2 settings keep their defaults.
Energy and Danceability are signal/rhythm **proxies**, not Spotify-equivalent
perceptual ratings. Vocal languages use conservative MusicBrainz evidence,
not audio speech recognition. Per-disc surface artwork is not implemented.

## Optional dependencies

Install these only if you need their features:

```bash
pip install "beets-noqlenmeta[discogs]"
pip install "beets-noqlenmeta[audio]"
```

See [supported versions](https://noqlen-meta.readthedocs.io/en/latest/technical-reference/compatibility/),
[troubleshooting](https://noqlen-meta.readthedocs.io/en/latest/troubleshooting/)
and the [MIT License](LICENSE). The complete manual lives on
[Read the Docs](https://noqlen-meta.readthedocs.io/en/latest/).
