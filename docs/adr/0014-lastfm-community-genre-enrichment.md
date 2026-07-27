# ADR 0014: Enrich genres conservatively from Last.fm community tags

- Status: Accepted
- Date: 2026-07-27

## Context

Last.fm album top tags can add useful community classification to a release already selected by
beets. They are popularity-weighted community labels, however, and are not typed as genre, style,
or mood. Raw social tags therefore cannot safely become canonical metadata.

## Decision

1. Last.fm is a community classification provider, not a release matcher.
2. It calls only `album.getTopTags` with the selected album artist/title and `autocorrect=0`; search,
   fuzzy matching, aliases, and fallback identities are excluded.
3. The response artist and album must match after only trimming, ordinary whitespace collapse, and
   case folding.
4. Block 018 supports `genres` only. Style and mood taxonomy inference is deferred.
5. Tags become genres only when their case-insensitive names occur in the vocabulary packaged at
   `beetsplug/lastgenre/genres.txt` by the supported beets installation.
6. LastGenre need not be enabled, its module is not imported, and no `pylast` dependency is added.
7. Noqlen reads the current `beets.plugins.LASTFM_KEY` at runtime. It does not copy, configure, log,
   expose, or persist that shared key.
8. Tags below weight 10 are discarded, accepted names are stably deduplicated, and at most three are
   emitted as one structured tuple.
9. The candidate confidence is fixed at `0.85`; tag weight remains only an internal quality filter.
10. Field Authority is unchanged and Provider Capabilities declare only genres. Discogs remains
    above Last.fm, Last.fm remains above iTunes, and Block 017 custom authority may reorder them.
11. Real requests are bounded to one megabyte, paced at least one second apart per provider instance,
    and repeated same-album lookups are cached in-process.
12. Expected service, authentication, rate-limit, and transport failures are fixed-message
    `ProviderError` values and remain fail-open. Defensible no-resource and no-accepted-genre results
    are empty.
13. Mapping, application, persistence, strict/partial policy, and file behavior do not change.
14. Default tests are deterministic and offline; one live production-boundary lookup is opt-in.

## Consequences

Last.fm can provide a useful fallback genre proposal without allowing ownership, activity, mood, or
other arbitrary community concepts into canonical fields. Future classification fields require an
explicit reviewed taxonomy rather than promotion of raw tags.
