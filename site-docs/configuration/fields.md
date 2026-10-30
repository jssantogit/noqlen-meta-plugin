# Fields

Fields choose **which kinds of metadata Noqlen is allowed to work with**.

```yaml
noqlenmeta:
  fields:
    genres: true
    styles: true
    moods: true
    bpm: true
    lyrics: false
    cover: true
```

A field set to `true` is eligible for enrichment when a suitable source and a
safe target exist. A field set to `false` is skipped. Field switches do not
write anything by themselves and do not enable providers.

## What each field means

| Field | Default | What it controls |
| --- | ---: | --- |
| `genres` | on | Canonical genre classification for the current release/library target. |
| `styles` | on | Ordered style or subgenre detail kept as a lossless multivalued field. |
| `labels` | on | Release label names. Multiple values can be blocked when the target is singular. |
| `catalog_numbers` | on | Label/catalog numbers attached to the release. |
| `barcodes` | on | Release barcodes such as UPC/EAN values when safely mapped. |
| `country` | on | Release country. An iTunes storefront is never treated as release country. |
| `year` | on | Release year selected from supported release evidence. |
| `media` | on | Release media/format such as CD where a lossless target exists; library application can be blocked when it does not. |
| `format_descriptions` | on | Detailed Discogs format descriptions. They can be resolved and previewed but currently have no lossless ordinary write target. |
| `moods` | on | Canonical track mood labels, bounded by `moods.max_moods`. |
| `bpm` | on | Track BPM metadata. This permits BPM handling but does **not** turn on local analysis. |
| `lyrics_languages` | on | Three-letter lyrics-language codes derived from exact MusicBrainz Recording-to-Work evidence. |
| `artist_countries` | on | Structurally identified artist country values from MusicBrainz area relationships. |
| `artist_areas` | off | Trustworthy MusicBrainz artist-area names. It is off by default because it is more detailed location metadata. |
| `artist_languages` | on | Contextual language codes derived only from Works reached by tracks in the current target. |
| `lyrics` | off | Plain track lyrics from LRCLIB when that provider is enabled. |
| `synced_lyrics` | off | Synchronized LRCLIB lyrics; existing-library application can create a verified no-clobber `.lrc` sidecar. Not an embedded SYLT tag. |
| `cover` | on | Album artwork handled through the verified Cover Art Archive pipeline. |
| `composers` | on | Structured Work composer relations plus native name/ID projections. |
| `lyricists` | on | Structured Work lyricist relations plus native name/ID projections. |
| `producers` | on | Recording- or Release-scoped producer relations without inheritance. |
| `arrangers` | on | Work- or Recording-scoped arranger relations. |
| `conductors` | on | Recording- or Release-scoped conductor relations. |
| `performers` | on | Performer relations with instruments preserved in structured database state. |
| `featured_artists` | on | Explicit featured or guest participation; vocals alone never qualify. |
| `structured_artist_credits` | on | Ordered MusicBrainz artist-credit nodes, credited names, MBIDs, and join phrases. |

The established V2 fields retain their original defaults; the older opt-ins
include `lyrics`, `synced_lyrics`, and `artist_areas`. All newly introduced V3
fields listed below are also **off unless explicitly configured**.

## Fields and feature settings are different

Some fields have a second configuration block that changes **how** the enabled
field behaves. For example:

```yaml
noqlenmeta:
  fields:
    moods: true

  moods:
    max_moods: 3
```

`fields.moods` permits mood enrichment. `moods.max_moods` then controls how many
supported moods may be retained. The same pattern applies to genres, artwork,
and BPM.

`local_analysis.mood.enabled` also exists in the complete configuration for
forward compatibility, but there is no implemented local mood-analysis model.

Use the topic pages for practical setup and the
[Fields Reference](../technical-reference/fields.md) for exact storage targets,
provider details, and mapping limitations.


## V3 optional Recording and audio fields (disabled until explicitly enabled)

The major-version enrichment fields are intentionally opt-in. Add only the
capabilities you want to the `noqlenmeta.fields` block:

| Field | Source / behavior | Storage |
| --- | --- | --- |
| `vocal_languages` | A single verified MusicBrainz Recording→Work performance relationship, excluding translated, instrumental and ambiguous versions | Typed multivalue Item, not audio language tags |
| `instrumental` | Positive explicit MusicBrainz/LRCLIB recording evidence; unknown is not false | Nullable Item |
| `explicitness` | Unique iTunes track-level explicit/clean advisory; missing advisory is unknown | Typed Item |
| `alternate_titles` | Exact MusicBrainz Recording aliases (no search suggestions) | Noqlen-owned SQLite records |
| `transliterations` | Only explicit MusicBrainz transliteration aliases | Noqlen-owned SQLite records |
| `track_version` | Whitelisted whole-string Recording disambiguation: radio edit, live version, etc. | Typed version/description Item fields |
| `back_artwork` | Exact-release CAA Back image, not a per-disc image | Verified `back.jpg` sidecar |
| `key` | Optional, conservative local pitch-class correlation | Native `Item.initial_key` |
| `energy` | RMS amplitude proxy, **not** perceptual energy | Nullable Item float + `energy_method` |
| `danceability` | Beat/onset regularity proxy, **not** a Spotify score | Nullable Item float + `danceability_method` |

`fields.key` also requires `local_analysis.key.enabled: true`.
`fields.energy` or `fields.danceability` also requires
`local_analysis.audio_features.enabled: true` and the optional `[audio]` extra.
These fields remain off unless explicitly supplied. Existing values and
unresolvable ambiguities are preserved, not guessed. Individual disc-surface
artwork is **not** a V3.0 feature.

For a tested, ready-to-adapt `noqlenmeta:` configuration and a safe preview
workflow, follow [Upgrade to V3](../recipes/v3-enrichment.md).
