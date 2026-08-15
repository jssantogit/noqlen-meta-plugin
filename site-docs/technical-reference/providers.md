# Provider Reference

Wave 1 reuses one concrete release acquisition for V2 candidates and V3 evidence. MusicBrainz is primary for release catalog and exact Recording/Work evidence; Discogs supplies secondary date and controlled edition evidence; iTunes is date fallback. MusicBrainz may add one exact Release Group support lookup only when requested group data is absent.

You will see each provider's real current scope and expected unavailable
behavior. Enabling a provider does not make it support every field.

| Provider | Enablement/credentials | Scope and fields | Ordinary library | Importer | Identity requirement |
| --- | --- | --- | ---: | ---: | --- |
| Discogs | `providers.discogs.enabled`; optional extra and token for search | Release catalog plus explicitly global producer, conductor, performer, featured, and guest credits | Yes | Yes | Direct release ID preferred; conservative search otherwise. Nonblank track scope is never promoted. |
| MusicBrainz enrichment | `providers.musicbrainz.enabled`; no plugin credential | Exact release catalog, Recording/Work identifiers, scoped core relationships, and ordered artist credits, plus existing semantic evidence | Yes | Yes | Exact existing Release/Recording/Work/Artist MBIDs; no fuzzy rematching. |
| Last.fm | `providers.lastfm.enabled`; uses beets' shared API key | Release, Track, Artist: classified genres, styles, moods | Yes | Yes | Scoped fallback while requested semantic fields remain unresolved. |
| iTunes | `providers.itunes.enabled`; no key; two-letter storefront | Release: genre, year | Yes | Yes | Direct collection/UPC preferred, then exact normalized search. |
| LRCLIB | `providers.lrclib.enabled`; no key | Track: plain and synchronized lyrics | Items | Yes | Exact title/artist/album/duration signature, about two-second duration tolerance; synchronized lyrics have no lossless writable target. |
| Cover Art Archive | `providers.coverartarchive.enabled`; no key; enabled by default | Album: one approved main front | Yes | Yes | Exact Release first; Release Group only after definitive absence/no eligible front. |
| MusicBrainz identity source | Importer `identity.enabled` or CLI `--identity`; no plugin credential | Separate four-MBID audit evidence | Identity mode only | Identity importer only | Structural candidate scoring and complete track assignment. |

MusicBrainz has an important distinction: its adapter capability tables describe
structured fields emitted directly at a scope, while the semantic pipeline can
also classify exact-entity community tags into canonical genres, styles, and
moods. Those classified values are still subject to field authority, confidence,
and mapping rules; unknown tags are not accepted.

## Requests, Pacing, And Caching

Network I/O stays behind each adapter. Provider adapters use bounded lookups,
timeouts, conservative in-process caches where implemented, and service-aware
pacing/retry behavior. Network time normally dominates enrichment. Caches are
process-local optimizations, not persistent product state or a guarantee that
a service will be available.

- Discogs prefers a direct release ID; search is bounded and can be ambiguous.
- MusicBrainz enrichment uses exact known MBIDs for the release and any required
  Recording, Work, Artist, or Area semantic lookups; it does not fuzzy-rematch
  those entities.
- Enabled Recording credits add only `artist-rels`; Work credits share one
  profile-aware exact Work payload with ISWC/language; Release credits reuse the
  exact Release payload. Disabling credits adds no relationship include.
- Discogs credits reuse the same concrete Release response. Track-scoped text
  and tracklist credits are currently omitted because no safe occurrence map is
  available at that adapter boundary.
- Last.fm contributes only vocabulary-classified semantic tags and is used as a
  scoped fallback while requested semantic fields remain unresolved.
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
return evidence below confidence. See [provider authority](../advanced/provider-authority-resolution.md).

`providers.musicbrainz.enabled` is only the enrichment adapter. It neither
enables nor disables identity audit or the MusicBrainz identity source.
