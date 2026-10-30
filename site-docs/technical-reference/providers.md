# Provider reference

This page lists **what each provider can actually contribute**. A provider
being enabled never guarantees that an album or track has matching evidence.
Noqlen prefers exact known identifiers and does not invent missing values.

| Provider | Setup | What it can supply | When/where it applies |
| --- | --- | --- | --- |
| **MusicBrainz enrichment** | On by default, no API key | Exact release catalog, Recording/Work IDs, structured credits, genre/style/mood evidence, verified Work-derived languages and Recording aliases | Existing-library Albums/Items and importer-selected material; known MBIDs required |
| **Cover Art Archive (CAA)** | On by default, no API key | Selected verified release front and opt-in **Back** image | Album `cover.jpg` and opt-in `back.jpg` sidecars, guarded on `--apply`; embedding supported for approved front art on `--write` |
| **LRCLIB** | Off by default, no API key | Plain lyrics, synchronized timestamped lyrics, explicit instrumental evidence when supported | Selected tracks or library Items; existing-library `--apply` can create a guarded `.lrc` sidecar, **not** embedded SYLT |
| **Discogs** | Off by default; optional `[discogs]` package extra and usually token for search | Release genres/styles, catalog numbers, dates/format details, and verified release-scoped credits | Album/release scope; conservative ID/search matching; tracklist credits aren't promoted without a safe track map |
| **Last.fm** | Off by default; beets shared API key | Classifiable genres, styles and moods as scoped fallback | Release, track and artist evidence; never an unconstrained tag dump |
| **iTunes** | Off by default; no key, choose two-letter storefront | Release genre/year fallback and uniquely matched exact-track **explicitness** advisory | Edition-aware release matches and strictly matched track advisory; storefront isn't country-of-release |
| **MusicBrainz identity source** | Independent identity command or importer identity flag | Separate four-MBID audit and repair evidence | Identity mode; toggling `providers.musicbrainz.enabled` does not switch it on/off |

!!! info "What will I see after enabling a provider?"
    Enable a relevant `fields` category, choose a suitable provider,
    then run a [preview](../start-here/reading-preview.md). A field can
    produce no result because a source lacks the necessary identifiers or
    safe evidence. For a ready-to-copy configuration, follow
    [configuration profiles](../recipes/configuration-profiles.md).

## Important V3 boundaries

- **LRCLIB:** plain lyrics and synchronized lyrics are distinct fields.
  The synchronized output is a verified `.lrc` file alongside the audio,
  only in eligible existing-library operations. There is no universal
  embedded SYLT writer.
- **Cover Art Archive:** front artwork and Back artwork are different
  release image types. `back.jpg` doesn't replace `cover.jpg` or
  `Album.artpath`. It doesn't represent individual CD/Medium surface art.
- **MusicBrainz:** Work-derived `vocal_languages` is a conservative
  relation-level inference, **not** audio language recognition.
- **iTunes:** absent explicit/clean advisory is *unknown*, not a proof of
  clean audio. A mismatched track is not treated as an advisory.
- **Local audio:** BPM, Key, Energy and Danceability are not online
  providers. They require the optional `[audio]` backend and independent
  `local_analysis` permissions.

For write-target restrictions, see the
[Field Reference](fields.md) and
[Where metadata is saved](../concepts/data-destinations.md).

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
