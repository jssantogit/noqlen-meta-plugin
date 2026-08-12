# Field Reference

You will see which ordinary fields can currently be supplied and where they
can be represented safely.

| Field | Default | Current providers | Importer target | Library target | Foundation result/limitation |
| --- | ---: | --- | --- | --- | --- |
| `genres` | on | MusicBrainz, Discogs, Last.fm, iTunes | Release list | Album list | Noqlen-resolved classification; one specific trustworthy genre by default, with no implicit parents. |
| `styles` | on | Discogs, MusicBrainz, Last.fm | Plural release field | Typed plural Album field | Source style/subgenre metadata and classified semantic style evidence remain ordered and lossless; recognized values may also inform `genres`, and scalar `style` is read only as a legacy fallback. |
| `labels` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `catalog_numbers` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `barcodes` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `country` | on | Discogs, MusicBrainz | Release country | Album country | iTunes storefront is never treated as release country. |
| `year` | on | MusicBrainz, Discogs, iTunes | Release year | Album year | MusicBrainz uses selected edition date. |
| `media` | on | Discogs, MusicBrainz | Release media | None | Importer can apply one value; library mode blocks. |
| `format_descriptions` | on | Discogs | None | None | Can be resolved and previewed, but has no lossless ordinary target. |
| `moods` | on | MusicBrainz, Last.fm | Typed track list | Typed Item list | Controlled canonical mood classification; bounded by `moods.max_moods`. |
| `bpm` | on | Optional local Librosa | Numeric track target | Float Item BPM | Existing values are preserved by default; local analysis is opt-in and failures stay track-local. |
| `lyrics_languages` | on | MusicBrainz | Typed track list | Typed Item list | Exact Recording-to-Work relationships supply three-letter language codes. |
| `artist_countries` | on | MusicBrainz | Typed track/album list | Typed Item/Album list | Structurally derived from identified artist area relationships. |
| `artist_areas` | off | MusicBrainz | Typed track/album list | Typed Item/Album list | Uses trustworthy main artist areas; never inferred from text. |
| `artist_languages` | on | MusicBrainz-derived Work evidence | Typed track/album list | Typed Item/Album list | Derived only from Work languages reached by tracks in the current target, not a direct artist-provider field. |
| `lyrics` | off | LRCLIB | Selected `TrackInfo.lyrics` | Item lyrics | Importer and existing-library Items share LRCLIB resolution. |
| `synced_lyrics` | off | LRCLIB | No lossless target | No lossless target | Previewed as blocked; synchronized lyrics/SYLT are not applied. |
| `cover` | on | Cover Art Archive | Album sidecar/embed | Album sidecar/embed | Exact approved main front; fixed `cover.jpg`; no singleton artwork. |

Provider candidates retain structured values. If beets offers only a singular
target and a provider offers multiple values, strict mode blocks the target;
partial mode may withhold only that field. Noqlen never picks the first value
or joins values to make them fit.

Genre classification uses the packaged Noqlen taxonomy and does not require
LastGenre. With style promotion enabled, a recognized Discogs style can win as
the resolved genre while remaining present in `styles`; this is intentional,
because the two fields preserve different semantics.

Ordinary `--apply --write` synchronizes only currently supported MediaFile
targets from the prepared plan. Identity workflows do not use this table or
field switches. They always handle exactly four MusicBrainz fields: release,
release group, recording, and release track IDs.

BPM is canonical `float`. `round: true` is useful for formats whose BPM tag
cannot preserve a fraction. Artwork remains a separate verified binary pipeline,
not an ordinary scalar field change.
