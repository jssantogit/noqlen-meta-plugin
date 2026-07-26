# Requirements - iTunes Album Enrichment and Multi-Provider Resolution

## Goal

Add a production iTunes Search API provider and prove that candidates from two real provider
boundaries coexist in one read-only Field Authority resolution pass.

## Functional requirements

- Resolve exactly one positive numeric `itunes.collection` identity directly, without search.
- Otherwise prefer a UPC/EAN lookup and permit one bounded text-search fallback only when no
  defensible UPC collection is found.
- Search albums with artist/title, music media, configured storefront, and a limit of 10 without
  pagination.
- Require normalized artist/title agreement and reject clear release-year conflicts or ambiguity.
- Emit only `primaryGenreName` as tuple-shaped `genres` and a valid `releaseDate` year.
- Preserve collection ID and a usable public collection URL as candidate provenance.
- Never emit store-facing `country`, lookup barcode, copyright-derived label, artwork, previews, or
  unsupported metadata.
- Keep Discogs and iTunes independently disabled by default and gate each provider by policy.
- Isolate each provider's expected failures and pass all successful candidates to one resolver call.
- Preserve existing per-field authority, including Discogs ahead of iTunes for genres.

## Safety requirements

- Do not mutate selected `AlbumInfo`, import task state, items, tags, files, or database records.
- Keep default tests offline and fixture-backed; gate live network access with
  `NOQLEN_LIVE_TESTS=1` and the `live` marker.
- Use HTTPS, an explicit User-Agent, a 10-second timeout, bounded response reading, and fixed safe
  `ProviderError` messages.

## Out of scope

Metadata application, provenance persistence, provider registries, caching, concurrency, Apple
Music authentication, artwork, previews, lyrics, mood, semantic genre union, fuzzy autotagging, and
CLI commands are excluded.
