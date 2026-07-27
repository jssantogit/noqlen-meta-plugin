# Design - Conservative Last.fm Genre Enrichment

## Flow

```text
selected album artist/title
  -> paced album.getTopTags (autocorrect=0)
  -> strict response identity validation
  -> weight >= 10
  -> packaged LastGenre vocabulary membership
  -> stable deduplication and first three
  -> one genres MetadataCandidate
```

`LastFmProvider` owns normalized-result caching. Its narrow transport owns standard-library HTTP,
the beets shared key, response bounds, and monotonic pacing. The plugin lazily retains one provider
instance so both behaviors survive across albums. Expected provider failures use the existing shared
fail-open collector; candidate contracts remain strict.

The immutable provider spec declares only `genres`. Existing authority selects Discogs before
Last.fm and Last.fm before iTunes unless configured authority replaces that order.
