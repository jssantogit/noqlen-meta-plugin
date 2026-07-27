# ADR 0017: Preview selected importer track plans

- Status: Accepted
- Date: 2026-07-27

## Context

Blocks 019 and 020 established selected track identity and exact LRCLIB candidates but deliberately
stopped before importer execution and current-state precedence. A safe first user-facing path must
mirror what beets will consider current after applying its selected metadata, reuse canonical
planning, and expose no lyric content or write authority.

## Decision

1. Track planning runs only for accepted importer `Action.APPLY` selections already represented by
   `AlbumMatch` or `TrackMatch`; Noqlen does not rematch.
2. An album match plans its selected Item-to-`TrackInfo` mapping in mapping order and excludes extra
   Items and extra TrackInfos. A singleton match produces one plan.
3. Track execution additionally requires `preview: true` and at least one enabled track provider
   capable of contributing to an enabled field under Field Authority. `apply` is not a track gate or
   track write permission.
4. LRCLIB is the only executed track provider in this block. Its adapter remains lazily constructed
   and retained on the plugin instance so provider cache, pacing, and Retry-After state survive across
   tracks.
5. The effective current-value baseline mirrors beets 2.12.x metadata application. Album selected
   metadata is `TrackInfo.merge_with_album(AlbumInfo)`; singleton selected metadata is
   `TrackInfo.item_data`.
6. With `from_scratch: false`, Item-local canonical values are retained and selected metadata is
   overlaid. With `from_scratch: true`, the model mirrors `Item.clear()`: writable media fields in
   Noqlen's modeled surface are cleared, flexible metadata survives, and selected metadata is then
   overlaid.
7. Consequently, when selected metadata omits both current fields, `from_scratch: true` clears
   `lyrics` but retains flexible `synced_lyrics`. A selected non-empty value overrides the baseline in
   either mode. Selected overlay is presence-sensitive: a field absent from beets' application mapping
   leaves the baseline untouched, while a present empty, blank, or otherwise non-canonical value still
   overwrites the Item and removes that canonical current value.
8. Baseline prediction is checked against actual `AlbumMatch.apply_metadata()` and
   `TrackMatch.apply_metadata()` across album/singleton, true/false `from_scratch`, `lyrics`/
   `synced_lyrics`, and selected-value absent/non-empty/empty/whitespace cases.
9. Track candidates use the existing provider capability gate, candidate contract validation, Field
   Authority, resolver, `FieldDecision`, and `ChangePlan`; no track-specific resolver or plan is
   introduced.
10. A `ProviderError` fails open for that provider call: its detail is discarded, a fixed sanitized
    warning is logged, an empty candidate set is planned, and later selected tracks continue.
11. Candidate/provider contract errors are programming or integration failures and propagate. They
    are not converted to provider unavailability or hidden by the preview path.
12. Release and track plans may coexist in one importer callback. Existing release planning,
    strict/partial selected-`AlbumInfo` application, and preview behavior run unchanged; track
    planning remains read-only even when `apply: true`.
13. With `preview: false`, existing release application remains available, but LRCLIB is not called
    and no track plan is built.
14. Preview includes sanitized selected identity, `from_scratch`, candidate and decision counts,
    actions, source, confidence, and reasons. Current and candidate lyric values are represented only
    by character and line summaries. Raw plain or synchronized lyrics are never rendered. An
    incomplete selected identity yields a fixed note without path data.
15. This block adds no track target map, mutation, application, database/store operation, tag write,
    file operation, or call to importer `apply_metadata()`. Noqlen only predicts the latter for
    planning.
16. The library CLI remains album-only and release-provider-only; it gains no singleton, per-track,
    or LRCLIB execution mode.
17. Beets does not model `synced_lyrics` as a standard persistent Item media field. The current beets
    Lyrics plugin stores canonical synchronized LRC text in `Item.lyrics` and passes native SYLT data
    separately for file writes. A future track application block must decide whether Noqlen's
    `synced_lyrics` means a flexible database value, a file-only synchronized tag, a mapping into
    canonical lyrics, or another explicit target. This block does not decide that mapping.

## Consequences

Users can review selected-track lyric decisions during import without exposing content or granting
new write authority. Planning truthfully reflects beets' current `from_scratch` behavior, including
the asymmetry between `lyrics` and flexible `synced_lyrics`. A later application block must define an
explicit target model and settle synchronized-lyrics persistence before any track mutation is added.
