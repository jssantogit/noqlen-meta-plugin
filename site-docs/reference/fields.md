# Field Reference

You will see which ordinary fields can currently be supplied and where they
can be represented safely.

| Field | Default | Current providers | Importer target | Library target | Foundation result/limitation |
| --- | ---: | --- | --- | --- | --- |
| `genres` | on | Discogs, Last.fm, iTunes | Release list | Album list | Noqlen-resolved classification; one specific trustworthy genre by default, with no implicit parents. |
| `styles` | on | Discogs | Plural release field | Typed plural Album field | Source style/subgenre metadata remains ordered and lossless; recognized values may also inform `genres`, and scalar `style` is read only as a legacy fallback. |
| `labels` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `catalog_numbers` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `barcodes` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `country` | on | Discogs, MusicBrainz | Release country | Album country | iTunes storefront is never treated as release country. |
| `year` | on | MusicBrainz, Discogs, iTunes | Release year | Album year | MusicBrainz uses selected edition date. |
| `media` | on | Discogs, MusicBrainz | Release media | None | Importer can apply one value; library mode blocks. |
| `format_descriptions` | on | Discogs | None | None | Can be resolved/previewed but v1 blocks application. |
| `moods` | on | None currently | Typed track list | Typed Item list | Foundation storage exists; semantic mood normalization is deferred. |
| `bpm` | on | None currently | Numeric track target | Built-in Item BPM | No analyzer/provider is delivered yet; fractional values block where beets would round them. |
| `lyrics_languages` | on | None currently | Typed track list | Typed Item list | Semantic MusicBrainz lookup is deferred. |
| `artist_countries` | on | None currently | Typed track/album list | Typed Item/Album list | Artist provider lookup is deferred. |
| `artist_areas` | off | None currently | Typed track/album list | Typed Item/Album list | Artist provider lookup is deferred. |
| `artist_languages` | on | None currently | Typed track/album list | Typed Item/Album list | Artist-language derivation is deferred. |
| `lyrics` | off | LRCLIB | Selected `TrackInfo.lyrics` | Item lyrics | Importer and existing-library Items share LRCLIB resolution. |
| `synced_lyrics` | off | LRCLIB | No lossless target | No lossless target | Previewed as blocked; synchronized lyrics/SYLT are not applied. |
| `cover` | on | None currently | None | None | Cover Art Archive/download/embed are deferred. |

Provider candidates retain structured values. If beets offers only a singular
target and a provider offers multiple values, strict mode blocks the target;
partial mode may withhold only that field. Noqlen never picks the first value
or joins values to make them fit.

Genre classification uses the packaged Noqlen taxonomy and does not require
LastGenre. With style promotion enabled, a recognized Discogs style can win as
the resolved genre while remaining present in `styles`; this is intentional,
because the two fields preserve different semantics.

Ordinary `--apply --write` synchronizes only currently supported MediaFile
targets from the prepared plan. Identity workflows do not use this table or field switches. They always handle
exactly four MusicBrainz fields: release, release group, recording, and release
track IDs.
