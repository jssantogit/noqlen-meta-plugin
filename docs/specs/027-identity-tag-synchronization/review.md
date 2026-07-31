# Block 027 Review

## Checklist

- One existing command, exclusive `--identity-tags`, and mode-local `--write` only.
- Complete Album expansion, singleton support, deterministic ordering, and no provider/audit work.
- Canonical coherent database identity and exact four-field allowlist; no partial synchronization.
- Preview creates no artifacts or writes; all planning/preflight precedes candidates.
- Source is never saved in place; candidate and backup remain same-directory and path-private.
- Candidate and replaced source verify all four targets, unrelated logical tags, and supported metadata.
- Safe failures restore; restoration failure is integrity-critical.
- Only Item `mtime` changes in the database; events occur after complete success only.
- The mutable pre-write `write` hook is omitted; success emits exact `after_write` then
  `database_change` signatures.
- Explicit source/mtime phases restore safe failures, retain path-private recovery backups for
  uncertain committed state, and prevent finalizer deletion of retained artifacts.
- Preview capability wording is noncommittal until a real candidate succeeds; invalid paths block
  without filesystem access while valid files continue.
- Candidate and backup-copy fallback source reads use `O_NOATIME` descriptors, never media-source
  `copy2`; unsupported atime-safe copies block before replacement.
- Safe restoration verifies original mtime and final link count one, while committed cleanup failures
  truthfully retain the still-existing original backup.
- No-op creates no artifacts/events; later failures report earlier per-file commits truthfully.
- Real FLAC, MP3, M4A, Ogg Vorbis, and Opus generated-silence round trips run offline.

## Outcome

Block 027 database-to-file MusicBrainz identity synchronization is complete. Preview remains the
default and only explicit `--identity-tags --write` replaces verified eligible files. Block 028 v1.0
Hardening and Release is next, then STOP.

The atime/copy correction passes 51 focused tests, 288 identity tests, and 1,088 full offline tests
with 5 live tests skipped. Ruff, repository contamination, and diff-whitespace checks pass.
