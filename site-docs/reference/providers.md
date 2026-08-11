# Provider Reference

You will see each provider's real current scope and expected unavailable
behavior. Enabling a provider does not make it support every field.

| Provider | Enablement/credentials | Scope and fields | Ordinary library | Importer | Identity requirement |
| --- | --- | --- | ---: | ---: | --- |
| Discogs | `providers.discogs.enabled`; optional extra and token for search | Release: genres, styles, labels, catalog numbers, barcodes, country, year, media, format descriptions | Yes | Yes | Direct release ID preferred; conservative search otherwise. |
| MusicBrainz enrichment | `providers.musicbrainz.enabled`; no plugin credential | Release: labels, catalog numbers, barcode, country, year, media | Yes | Yes | Exact existing release MBID; no fuzzy rematching. |
| Last.fm | `providers.lastfm.enabled`; no user key setting | Release: filtered genres | Yes | Yes | Selected artist/album; community tags filtered through beets genre vocabulary. |
| iTunes | `providers.itunes.enabled`; no key; two-letter storefront | Release: genre, year | Yes | Yes | Direct collection/UPC preferred, then exact normalized search. |
| LRCLIB | `providers.lrclib.enabled`; no key | Track: plain and synchronized lyrics | No | Yes | Exact title/artist/album/duration signature, about two-second duration tolerance. |
| Cover Art Archive | `providers.coverartarchive.enabled`; no key; enabled by default | Album: one approved main front | Yes | Yes | Exact Release first; Release Group only after definitive absence/no eligible front. |
| MusicBrainz identity source | Importer `identity.enabled` or CLI `--identity`; no plugin credential | Separate four-MBID audit evidence | Identity mode only | Identity importer only | Structural candidate scoring and complete track assignment. |

## Requests, Pacing, And Caching

Network I/O stays behind each adapter. Provider adapters use bounded lookups,
timeouts, conservative in-process caches where implemented, and service-aware
pacing/retry behavior. Network time normally dominates enrichment. Caches are
process-local optimizations, not persistent product state or a guarantee that
a service will be available.

- Discogs prefers a direct release ID; search is bounded and can be ambiguous.
- MusicBrainz enrichment performs one exact release lookup.
- Last.fm contributes at most three accepted weighted genres.
- iTunes examines at most ten search results and requests no artwork/previews.
- LRCLIB uses exact `/api/get`, has no search fallback, and preserves raw lyrics
  privately while preview displays counts only.
- Cover Art Archive metadata selection occurs during planning. Image bytes are
  downloaded only while applying the prepared plan; transient exact-Release
  failure never falls back to a different edition.

## Unavailable Providers

A provider timeout, service error, missing optional Discogs dependency, or no
defensible exact result contributes no candidates. Noqlen emits a provider-safe
warning and continues with other eligible providers. Raw provider errors and
tokens are not displayed.

No result can also be normal: the provider may not support the enabled field,
may lack the required identity, may not appear in field authority, or may
return evidence below confidence. See [field authority](../concepts/providers-and-field-authority.md).

`providers.musicbrainz.enabled` is only the enrichment adapter. It does not
enable or disable the MusicBrainz identity source.
