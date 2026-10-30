# Choose a task

Don't start with a 100-line YAML file. **Pick the result you want**, follow
one recipe, preview one track or album, and only then apply changes.

| What I want | Recipe | Main requirement |
| --- | --- | --- |
| Try Noqlen safely | [Quickstart](../start-here/quickstart.md) | Album already in beets |
| Choose a practical config | [Configuration profiles](configuration-profiles.md) | Merge into existing config |
| Enrich a whole album | [Existing library](existing-library.md) | Beets match/IDs |
| Enrich while importing | [During import](import-enrichment.md) | Independent importer permissions |
| Add album covers | [Front and back artwork](artwork.md) | Verified CAA release |
| Add plain or synced lyrics | [Lyrics and LRC](lyrics-synced.md) | LRCLIB enabled |
| Add credits and Recording/Work details | [Recording credits](recording-credits.md) | Known MusicBrainz IDs |
| Calculate BPM and Key and optional proxies | [Local audio analysis](audio-analysis.md) | Optional `[audio]` extra |
| Calculate only BPM | [BPM-only](local-bpm.md) | Optional `[audio]` extra |
| Add music-language context | [Lyrics and languages](lyrics-languages.md) | Work evidence |
| Upgrade from V2 | [V3 upgrade guide](v3-enrichment.md) | Back up and selectively opt in |
| Repair wrong MusicBrainz identities | [Identity repair](repair-musicbrainz-ids.md) | Separate identity mode |
| Safely process many albums | [Whole library](whole-library.md) | Single-album dry run first |

Every guide distinguishes the **configuration**, **preview**, **application**
and **storage destination**. Ambiguous values can be withheld for review.

Not sure why a field can be enabled yet produce no result? Read
[How Noqlen works](../concepts/mental-model.md),
[Data destinations](../concepts/data-destinations.md), or
[Troubleshooting](../troubleshooting/index.md).

All exact settings and supported file targets live in the
[Technical Reference](../technical-reference/index.md).
