# Block 024 Requirements

## Goal

Provide a conservative, read-only MusicBrainz identity audit result for an immutable local album
context and hydrated release candidates.

## Required behavior

- Audit exactly `mb_albumid`, `mb_releasegroupid`, `mb_trackid`, and `mb_releasetrackid`.
- Validate complete canonical candidate UUIDs while retaining malformed existing IDs for comparison.
- Normalize text conservatively without removing semantic edition markers.
- Assign tracks globally with title, duration, artist, and multidisc position evidence.
- Score structural evidence from 0 to 100 without consuming existing IDs.
- Require conservative score, margin, pair, completeness, and uniqueness policy checks.
- Return confirmed, missing, conflict, or ambiguous with deterministic findings and rankings.
- Acquire bounded hydrated candidates through injectable beets MusicBrainz facilities, preserving
  sorted exact-ID priority followed by primary and singleton alternate search relevance order.
- Deduplicate acquisition by first canonical release-MBID occurrence; acquisition position must never
  affect structural score or candidate margin.
- Keep all default tests offline and all production behavior read-only.

## Exclusions

No importer or CLI integration, mutation, persistence, tag/file writes, AcoustID, recording search,
new configuration, provider redesign, or resolver/ChangePlan reuse.
