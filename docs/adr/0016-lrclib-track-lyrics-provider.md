# ADR 0016: Add an exact-signature LRCLIB track lyrics provider

- Status: Accepted
- Date: 2026-07-27

## Context

Block 019 established selected track identity and a track provider contract while retaining the
canonical candidate, Field Authority, resolver, and `ChangePlan`. LRCLIB can provide plain and
synchronized lyrics, but it must enrich the track beets selected rather than become another matcher.

## Decision

1. LRCLIB is track-scoped and supports exactly `lyrics` and `synced_lyrics`.
2. Existing canonical fields, shared planning contracts, and unchanged default Field Authority are
   reused; there is no global LRCLIB priority.
3. LRCLIB is disabled by default and requires no API credentials.
4. Production uses only the exact-signature HTTPS `GET /api/get` endpoint. Search fallback is
   forbidden.
5. Track artist/title come unchanged from the selected `TrackEnrichmentContext`; album title and
   duration are mandatory request prerequisites.
6. Missing album title or duration is quiet no-data and performs no network request.
7. Returned artist, title, and album are revalidated using only trim, ordinary-whitespace collapse,
   and case folding.
8. Returned duration must be finite, positive, and within +/-2 seconds of the request.
9. A successful record requires a positive integer LRCLIB ID and a real boolean instrumental flag.
10. HTTP 404 is normal no-data. Network failures, service failures, malformed responses, identity or
    duration mismatch, and oversized responses are fixed safe `ProviderError` values.
11. Instrumental records emit no candidates.
12. Plain and synchronized lyrics are independent fields; neither representation is synthesized,
    translated, cleaned, or converted from the other.
13. Candidate confidence is fixed at `0.95` and provenance uses the decimal LRCLIB record ID with a
    public record URL rather than the metadata-bearing request URL.
14. Requests identify `beets-noqlenmeta`, installed package version (or `0+unknown`), and the generic
    public PyPI project page without credentials or personal identifiers.
15. Requests are sequential within one transport instance and paced with monotonic time at a minimum
    interval of 0.3 seconds.
16. A valid HTTP 429 `Retry-After` seconds value creates a barrier for subsequent requests; the
    current lookup is not retried. Invalid Retry-After remains a fixed safe error.
17. Same-signature successful records and 404/no-data results are cached in-process. Errors are not
    cached; there is no disk cache, TTL system, or general cache framework.
18. Responses are bounded to 2 MiB and raw response bodies, plain lyrics, synchronized lyrics, and
    candidate values are never logged.
19. Fixture lyrics are synthetic, default tests are offline, and live validation is opt-in with one
    exact request and no lyric-content assertions or output.
20. LRCLIB joins `BUILTIN_TRACK_PROVIDER_SPECS`, not the release registry. Existing release importer
    and CLI orchestration do not execute it.
21. Track current-value composition, target mapping, TrackInfo or Item mutation, database persistence,
    and physical file writes remain deferred to separately reviewed work.

## Consequences

LRCLIB records can pass through the existing canonical resolution and planning engine without track
matching or a parallel resolver. Enabling LRCLIB alone cannot start album importer or library-command
work, and no current production path applies lyrics.
