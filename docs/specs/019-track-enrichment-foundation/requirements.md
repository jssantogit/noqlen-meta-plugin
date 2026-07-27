# Requirements - Track Enrichment Foundation

## Goal

Add provider-independent track identity, read-only beets adapters, and entity-scoped provider
contracts for future track providers without adding track execution or writes.

## Requirements

- Require trimmed non-empty track artist/title and conservatively validate optional album, duration,
  numbering, MusicBrainz IDs, ISRCs, and AcoustID track IDs.
- Treat generic `TrackInfo.track_id` and `release_track_id` as MusicBrainz only for a MusicBrainz
  `data_source`; separately validate explicit carried MB fields.
- Parse multiple ISRCs only from semicolon-separated beets values and stable-deduplicate identifiers.
- Exclude fingerprints and avoid Item-to-Album fallback reads.
- Expose selected `AlbumMatch` pairs and singleton `TrackMatch` without rematching or mutation.
- Expose TrackInfo and Item lyrics current values separately; defer importer merge precedence.
- Separate release/track provider protocols and specs while retaining one candidate/resolver/planner.
- Keep all existing providers and album importer/CLI orchestration release-scoped and unchanged.

## Out Of Scope

Track providers, network calls, matching, target mapping, application, persistence, file writes,
fingerprinting, cache, concurrency, and track CLI modes are excluded.
