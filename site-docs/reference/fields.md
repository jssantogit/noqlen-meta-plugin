# Field Reference

You will see which ordinary fields can currently be supplied and where they
can be represented safely.

| Field | Default | Current providers | Importer target | Library target | v1 result/limitation |
| --- | ---: | --- | --- | --- | --- |
| `genres` | on | Discogs, Last.fm, iTunes | Release list | Album list | Applies losslessly as a list. |
| `styles` | on | Discogs | Singular release field | Singular Album field | Multiple values block; never joined silently. |
| `labels` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `catalog_numbers` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `barcodes` | on | Discogs, MusicBrainz | Singular release field | Singular Album field | Multiple values block. |
| `country` | on | Discogs, MusicBrainz | Release country | Album country | iTunes storefront is never treated as release country. |
| `year` | on | MusicBrainz, Discogs, iTunes | Release year | Album year | MusicBrainz uses selected edition date. |
| `media` | on | Discogs, MusicBrainz | Release media | None | Importer can apply one value; library mode blocks. |
| `format_descriptions` | on | Discogs | None | None | Can be resolved/previewed but v1 blocks application. |
| `mood` | off | None currently | None | None | No current provider contribution. |
| `lyrics` | off | LRCLIB | Selected `TrackInfo.lyrics` | None | Importer-only plain lyrics; ordinary library mode is album-only. |
| `synced_lyrics` | off | LRCLIB | No lossless target | None | Previewed as blocked; v1 never applies synchronized lyrics/SYLT. |
| `cover` | off | None currently | None | None | v1 does not fetch or write cover art. |

Provider candidates retain structured values. If beets offers only a singular
target and a provider offers multiple values, strict mode blocks the target;
partial mode may withhold only that field. Noqlen never picks the first value
or joins values to make them fit.

Identity workflows do not use this table or field switches. They always handle
exactly four MusicBrainz fields: release, release group, recording, and release
track IDs.
