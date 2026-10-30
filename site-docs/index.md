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

## Choose what you want to do

<div class="grid cards" markdown>

- **I'm new — show me how**

    ---

    Install Noqlen, preview one album and understand the safety controls.

    [Start the guided quickstart](start-here/quickstart.md)

- **I want to customize my music**

    ---

    Pick a goal, use a ready-to-adapt configuration and add more features.

    [Browse task-based recipes](recipes/index.md)

- **I want to combine features**

    ---

    Turn on lyrics, analysis and other sources without breaking YAML mappings.

    [Learn to combine settings](recipes/combine-features.md)

- **I don't understand a result**

    ---

    Learn what KEEP, PROPOSE, REVIEW and BLOCKED mean, with a worked example.

    [Read a preview](start-here/reading-preview.md)

- **I want to know where data is saved**

    ---

    Distinguish the beets database, `.lrc`/`cover.jpg` sidecars and audio tags.

    [See data destinations](concepts/data-destinations.md)

- **I need every option and default**

    ---

    Find exact field, provider, command and compatibility contracts.

    [Open the technical reference](technical-reference/index.md)

</div>

### Popular tasks

[Add artwork](recipes/artwork.md) ·
[Synchronized lyrics](recipes/lyrics-synced.md) ·
[Recording/Work credits](recipes/recording-credits.md) ·
[Local BPM and Key](recipes/audio-analysis.md) ·
[MusicBrainz identity repair](recipes/repair-musicbrainz-ids.md)

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
