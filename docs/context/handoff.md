# Handoff

## State

Block 027 is complete. Database-to-file MusicBrainz identity synchronization exists as explicit
`--identity-tags` mode on the existing `noqlenmeta`/`nm` command.

## Completed

- Exclusive mode validation with query-or-`--all` selection, complete Album expansion, standalone
  Items, deterministic ordering, and no provider/source/audit work.
- Preview by default; only CLI `--write` permits file replacement and operational `mtime` update.
- Fresh immutable path-private database snapshots with complete canonical Album/singleton coherence.
- Exact no-follow source fingerprints and safely frozen four-field/unrelated MediaFile snapshots.
- Missing/conflict/malformed statuses and immutable canonical four-field plans.
- Whole-command planning and fresh database/stat preflight before the first candidate.
- Same-directory extension-preserving candidates that write and verify all four fields without
  opening the source for save.
- Unrelated logical tag and supported filesystem metadata verification.
- Same-directory rollback backup before `os.replace`, replaced-source verification, safe restoration,
  and integrity-critical restore failure handling.
- Fixed-column savepoint update of only Item `mtime`, followed by fresh verification and standard
  post-success `after_write` and `database_change` events. The mutable pre-write `write` hook is not
  emitted.
- Explicit source/mtime commit phases, safe restoration, and retained path-private recovery backup for
  integrity-critical uncertain commit state.
- Truthful per-file capability rendering and blocked empty/invalid persisted paths without filesystem
  access or interruption of valid files.
- Candidate and backup-copy fallback source reads through `O_NOATIME` no-follow descriptors, with no
  production media-source `copy2`; unsupported atime-safe copies block before replacement.
- Safe restoration verifies original mtime and final link count one, and committed cleanup failure
  retains the path-private original backup truthfully.
- Immediate privacy-safe rendering, no-op behavior, and truthful later committed-state reporting.
- Offline generated-silence production round trips for FLAC, MP3, M4A, Ogg Vorbis, and Opus.
- Validation: 51 focused fix tests, 288 identity tests, and 1,088 full offline tests pass with 5 live
  tests skipped; Ruff, contamination, and diff-whitespace checks pass.

## Important Decisions

- Database identity is authoritative but must be canonical and internally coherent.
- Exactly four MusicBrainz fields are writable; conflicting/malformed file identity is synchronized.
- `--apply` and importer configuration never authorize tag writes.
- Source paths are private and source files are never saved in place.
- Files commit independently; there is no command-wide filesystem rollback claim.

## Deferred

- Block 028 final configuration/UX/package/documentation compatibility and release hardening.
- AcoustID, Chromaprint, fingerprinting, recording search, and new metadata features remain outside
  v1.0.

## Next Direction

Proceed to Block 028, then STOP.
