# Block 027 Design

## Flow

```text
validate exclusive CLI mode
  -> Block 026 Item-query selection and complete target expansion
  -> fresh path-private database snapshots and coherence validation
  -> exact no-follow stat plus MediaFile logical snapshots
  -> immutable four-field plans for every file
  -> command-wide database/stat preflight
  -> same-directory complete candidate copy through O_NOATIME source descriptor
  -> write and reopen/verify four fields plus unrelated tags and filesystem metadata
  -> rollback backup, os.replace, and replaced-source verification
  -> fixed-column mtime savepoint and fresh verification
  -> post-success after_write/database_change events
  -> immediate privacy-safe result
```

## Modules

- `identity/tag_sync.py`: selected file boundary, fresh database snapshots, and target coherence.
- `identity/tag_filesystem.py`: exact fingerprints, logical MediaFile freezing, and metadata checks.
- `identity/tag_mapping.py`: statuses, canonical immutable plans, and command-wide file planning.
- `identity/tag_application.py`: plan integrity, candidate/backup/replace/restore, mtime, and events.
- `identity/tag_preview.py`: path-free per-file rendering.
- Plugin entry point: exclusive CLI validation, reused selection, preflight, sequential application.

The fingerprint is a conservative stale guard for ordinary concurrency, not a hostile-process
security boundary. MediaFile remains the sole owner of format-specific mappings. File/database
atomicity is per Item; previously completed files are never represented as command-wide rolled back.

Application explicitly tracks source-unchanged, source-replaced, and mtime-committed phases. Safe
mtime rollback restores the backup. Commit-uncertain or rollback-failed mtime state is
integrity-critical and committed because source replacement occurred; its original backup is retained
as a path-private recovery artifact and excluded from finalizer deletion. Confirmed post-commit
failure never triggers blind restoration.

The beets `write` event is intentionally omitted because it is a mutable pre-write hook incompatible
with the immutable verified candidate. Successful delivery is `after_write(item, path)` followed by
`database_change(lib, model)` only after file/database verification. Preview creates no candidate and
does not claim per-file round-trip capability. Invalid persisted paths use a separate blocked boundary
and never enter stat, MediaFile, candidate, or replacement code.

Candidate and backup-copy fallback byte reads share one descriptor-based primitive. It opens the
source with `O_NOATIME | O_NOFOLLOW`, writes through the retained `mkstemp` descriptor or an
exclusively created backup descriptor, fsyncs, applies supported metadata through the descriptor, and
requires exact source fingerprint and metadata equality afterward. There is no normal path-based
source copy fallback. Safe restoration additionally requires original mtime and final link count one;
inode and ctime are intentionally not universal restoration requirements.
