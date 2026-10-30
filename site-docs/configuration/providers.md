# Providers

Providers are metadata sources. Enable a provider only when its contribution is
useful to the fields you selected.

```yaml
providers:
  musicbrainz:
    enabled: true
  coverartarchive:
    enabled: true
```

MusicBrainz is the zero-credential semantic backbone for exact known IDs across
release, track, Work, and artist metadata. Cover Art Archive supplies verified
release-front artwork and, when explicitly enabled, exact-release Back images.
Both providers are enabled by default and need no API key.

Discogs contributes release genres, ordered styles, labels, catalog numbers,
barcodes, country, year, media, and format descriptions. Direct-ID lookup can
work without credentials; search needs the optional Discogs dependency and
generally a token from `NOQLENMETA_DISCOGS_TOKEN`.

Last.fm contributes classified genres, styles, and moods at release, track, and
artist scope and uses beets' shared API key. iTunes contributes release genres
and year; its two-letter `storefront` is a search storefront, never release
country. LRCLIB supplies track plain and synchronized lyrics without an API key,
and guarded `.lrc` sidecars for existing-library Items when enabled.

Example field/source relationship:

```yaml
fields:
  lyrics: true
  synced_lyrics: false
providers:
  lrclib:
    enabled: true
```

See [Providers Reference](../technical-reference/providers.md) for capability
and prerequisite matrices. Semantic MusicBrainz enablement neither enables nor
disables identity audit.


In V3, iTunes may also provide exact-track explicit/clean advisory evidence.
MusicBrainz can support conservative `vocal_languages` only when an unambiguous
Recording-to-Work relation permits the derivation. These are not guesses from
artist nationality or release language. See the
[V3 upgrade recipe](../recipes/v3-enrichment.md) for the opt-in switches.
