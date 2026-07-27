# Requirements - Conservative Last.fm Genre Enrichment

## Goal

Add Last.fm as a disabled-by-default built-in provider that enriches only the selected album's
genres from vocabulary-validated community top tags.

## Requirements

- Use `album.getTopTags` with selected artist/title and `autocorrect=0`; never search or rematch.
- Read `beets.plugins.LASTFM_KEY` at runtime and expose no Last.fm credential configuration.
- Load the packaged LastGenre vocabulary without importing LastGenre or requiring `pylast`.
- Validate response identity conservatively, require weight at least 10, and accept at most three
  stably deduplicated vocabulary genres.
- Emit zero or one `genres` candidate at confidence `0.85` with safe public provenance.
- Bound and pace network requests, cache same-album results per provider instance, and fail open
  through fixed-message `ProviderError` handling.
- Preserve existing resolver, mapping, application, persistence, and file semantics.

## Out of scope

Styles, mood, taxonomy inference, search, fuzzy matching, authentication, persistent caching,
concurrency, new settings, and write-path changes are excluded.
