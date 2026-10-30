# Noqlen Meta — improve your music metadata, safely

**Noqlen Meta is an optional [beets](https://beets.io/) plugin** that adds
evidence-backed metadata to music already matched by beets. You choose
which fields and sources to use; Noqlen previews proposed changes before
you authorize them.

**New to Noqlen?** Try one album first:

```bash
pip install beets-noqlenmeta
beet nm album:"Discovery"
```

First enable `noqlenmeta` in your existing beets `plugins:` list and
replace `Discovery` with an album **already imported** into your library.
This command previews only. The [guided quickstart](start-here/quickstart.md)
shows every step and explains the results.

## What do you want to do?

| My goal | Step-by-step guide |
| --- | --- |
| Get started without changing my files | [Quickstart: one album](start-here/quickstart.md) |
| Set up a few common features | [Configuration profiles](recipes/configuration-profiles.md) |
| Improve genres, styles, moods or release metadata | [Configuration overview](configuration/index.md) |
| Add album covers and back artwork | [Artwork recipe](recipes/artwork.md) |
| Add lyrics or synchronized `.lrc` files | [Lyrics recipe](recipes/lyrics-synced.md) |
| Add composers, performers and Recording/Work details | [Recording credits recipe](recipes/recording-credits.md) |
| Analyze BPM, Key, Energy or Danceability locally | [Audio analysis recipe](recipes/audio-analysis.md) |
| Repair MusicBrainz identities | [Identity recipe](recipes/repair-musicbrainz-ids.md) |
| Find every option, default and write target | [Technical reference](technical-reference/index.md) |

## How does it work?

```text
Choose the fields  ->  Choose sources  ->  Preview evidence
                                              |
                                              v
                              Apply to beets database if safe
                                              |
                                              v
                             Optionally write supported file tags
```

The three questions users ask most often:

- **What can I enrich?** `fields` selects metadata categories, while
  `providers` and optional `local_analysis` supply the evidence.
  See [the mental model](concepts/mental-model.md).
- **Where will it go?** Database-only values, verified sidecars
  (`cover.jpg`, `back.jpg`, `.lrc`) and embedded audio tags have different
  rules. See [data destinations](concepts/data-destinations.md).
- **What if sources disagree?** Noqlen can keep the old value,
  propose one, request review or block an unsafe change. See
  [understanding results](start-here/understanding-results.md).

!!! info "New V3 features are opt-in"
    The established V2 defaults are preserved. Key, Energy and Danceability
    require optional audio analysis. Energy and Danceability are signal/rhythm
    proxies, **not** Spotify-equivalent scores. Vocal languages are derived
    from conservative MusicBrainz relationships, not recognized directly
    from audio. Individual disc-surface artwork is not supported.

## Documentation and releases

This documentation is organized by **task first**, with deeper
[concepts](concepts/mental-model.md), [troubleshooting](troubleshooting/index.md)
and [reference](technical-reference/index.md) for when you need them.

- [Python package on PyPI](https://pypi.org/project/beets-noqlenmeta/)
- [GitHub repository](https://github.com/jssantogit/noqlen-meta-plugin)
- [Release status and documentation versions](project/release.md)
- [MIT License](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)

The canonical public documentation is live at
[https://noqlen-meta.readthedocs.io/en/stable/](https://noqlen-meta.readthedocs.io/en/stable/).
Until the next documentation tag is published and activated, choose
[latest](https://noqlen-meta.readthedocs.io/en/latest/) for the ongoing V3
manual; the stable alias may still show an older snapshot. The original V3
package release was 3.0.0 on October 30, 2026.
