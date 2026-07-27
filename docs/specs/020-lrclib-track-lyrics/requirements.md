# Requirements - LRCLIB Track Lyrics Provider

## Goal

Add LRCLIB as the first real track-scoped provider, using only the selected exact track signature and
stopping after the shared canonical `ChangePlan` boundary.

## Requirements

- Register immutable track-only capability for `lyrics` and `synced_lyrics`, disabled by default.
- Require selected artist, title, album title, and duration; missing optional prerequisites are quiet
  no-data without network access.
- Use only HTTPS `GET /api/get`, identify the client safely, bound responses to 2 MiB, and use a
  10-second timeout.
- Revalidate positive record ID, response identity, duration within +/-2 seconds, instrumental flag,
  and nullable lyric field shapes.
- Emit independent ordered candidates with confidence `0.95` and record-ID provenance.
- Pace requests, honor valid 429 Retry-After barriers, and cache successful/404 signatures only.
- Convert expected external failures to fixed safe `ProviderError` values and never log lyrics.
- Keep default tests offline with synthetic fixtures and one opt-in exact live smoke.
- Preserve release-only importer/CLI behavior and add no mapping, mutation, persistence, or file I/O.

## Out Of Scope

Search, fuzzy matching, identity cleanup, lyric conversion, track execution, target mapping,
application, database or file writes, persistent cache, credentials, concurrency, and other track
providers are excluded.
