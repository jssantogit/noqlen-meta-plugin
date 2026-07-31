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
- No-op creates no artifacts/events; later failures report earlier per-file commits truthfully.
- Real FLAC, MP3, M4A, Ogg Vorbis, and Opus generated-silence round trips run offline.

## Outcome

Block 027 database-to-file MusicBrainz identity synchronization is complete. Preview remains the
default and only explicit `--identity-tags --write` replaces verified eligible files. Block 028 v1.0
Hardening and Release is next, then STOP.
