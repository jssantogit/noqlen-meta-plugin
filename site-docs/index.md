# Noqlen Meta

**Noqlen Meta 3.x** is a music-metadata enrichment plugin for
[beets](https://beets.io/). It supplements beets' own matching and library
management rather than choosing replacement album or recording matches.

Noqlen proposes supported release, Recording, Work, and artist metadata from
focused sources. **Preview is the default**: database application, verified
artwork/lyrics sidecars, and writing tags to audio files remain separate,
explicit actions.

## What it can add

| Area | Capabilities |
| --- | --- |
| Release metadata | Genres, styles, moods, dates, labels, countries, catalog details, and verified front cover artwork |
| Recording and Work | ISRC/ISWC/Work references, credits with role and instrument details, typed alternate titles/transliterations, and recording versions |
| Language and lyrics | Plain lyrics, opt-in synchronized `.lrc` sidecars, and conservative opt-in vocal-language evidence |
| Artwork | Verified `cover.jpg` front and opt-in `back.jpg` back artwork for the exact release |
| Local audio | Optional BPM, conservative musical Key, and versioned signal-based Energy / rhythmic Danceability indices |
| Identity | Separate MusicBrainz identity repair and AcoustID-assisted evidence workflows |

Some V3 capabilities are **off by default**. They require explicit field and
provider/local-analysis settings. A missing or conflicting result is not guessed.

!!! note "Energy and Danceability are proxies"
    The optional 0–1 Energy score measures decoded audio RMS intensity, while
    Danceability measures beat/onset regularity. They are *not* calibrated
    human-perceptual or Spotify-equivalent ratings.

!!! note "Scope limitations"
    Vocal languages are derived only from sufficiently verified MusicBrainz
    Recording→Work relationships, not recognized directly from the audio.
    Individual CD/Medium surface artwork is not supported in 3.0.0.

## Get started

New to beets? Follow [Start Here](start-here/index.md) for installation,
configuration, preview, safe database application, and optional file writing.

Already using Noqlen 2.x? See the
[V3 enrichment recipe](recipes/v3-enrichment.md) for opt-in configuration and
upgrade notes, or open the [Field Reference](technical-reference/fields.md)
for precise storage and limitations.

## Releases and project

- [GitHub releases](https://github.com/jssantogit/noqlen-meta-plugin/releases)
- [Install from PyPI](https://pypi.org/project/beets-noqlenmeta/)
- [Release history and documentation versions](project/release.md)
- [GitHub repository](https://github.com/jssantogit/noqlen-meta-plugin)
- [MIT License](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)

The canonical documentation is
[noqlen-meta.readthedocs.io/en/stable/](https://noqlen-meta.readthedocs.io/en/stable/).
The initial V3 release (`3.0.0`) shipped on October 30, 2026. The `3.0.1`
documentation-only patch incorporates the updated manual. Read the Docs
versioned pages are built from their respective Git tags; use the selector
to read the documentation for the version you installed.
