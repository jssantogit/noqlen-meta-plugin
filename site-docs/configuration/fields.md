# Fields

Fields choose **which kinds of metadata Noqlen is allowed to work with**.

```yaml
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
| `synced_lyrics` | off | Synchronized LRCLIB lyrics. They can be previewed as blocked, but Noqlen currently has no lossless writable target for them. |
| `cover` | on | Album artwork handled through the verified Cover Art Archive pipeline. |

Most fields default on. The deliberate opt-ins are `lyrics`, `synced_lyrics`,
and `artist_areas`.

## Fields and feature settings are different

Some fields have a second configuration block that changes **how** the enabled
field behaves. For example:

```yaml
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
