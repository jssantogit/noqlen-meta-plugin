# Design - iTunes Album Enrichment and Multi-Provider Resolution

## Provider flow

```text
ReleaseEnrichmentContext
        -> one explicit itunes.collection lookup, or
        -> UPC lookup, then at most one bounded artist + album search
        -> one defensible collectionId
        -> genres/year MetadataCandidate values
```

An explicit identity is accepted only when exactly one positive numeric identifier exists and the
lookup returns exactly that collection. It uses confidence `0.98` and never falls back. UPC results
must agree with selected artist/title and any useful year; one unique collection uses `0.94`,
ambiguity stops resolution, and no match permits one text search. Text search uses `media=music`,
`entity=album`, `limit=10`, no pagination, and confidence `0.82` for one unique match.

Matching uses Unicode normalization, case folding, whitespace collapse, and conservative punctuation
handling. It does not remove edition suffixes or perform fuzzy matching. Emitted values retain the
API's metadata text rather than the matching-normalized form.

## HTTP boundary

The standard-library boundary issues HTTPS requests to the public iTunes Search API with a User-Agent,
10-second timeout, and one-megabyte response cap. It decodes a JSON object with a result sequence.
Expected HTTP, URL, timeout, decoding, and malformed-wrapper failures become the fixed safe message
`iTunes API request failed`; unrelated programming errors remain visible.

## Multi-provider orchestration

The plugin explicitly gates Discogs and iTunes with `provider_can_contribute()`. Each enabled provider
is called independently and only its own `ProviderError` is skipped. Successful candidates are
appended to one sequence and sent through one `resolve_metadata()` call. Existing authority chains are
unchanged, so eligible Discogs genres beat higher-confidence iTunes genres while iTunes remains the
fallback when Discogs has no eligible candidate.

The preview maps `discogs` to `Discogs` and `itunes` to `iTunes`; unknown future names use safe title
casing. Decisions remain preview-only.
