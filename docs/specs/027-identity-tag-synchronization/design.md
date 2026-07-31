# Block 027 Design

## Flow

```text
validate exclusive CLI mode
  -> Block 026 Item-query selection and complete target expansion
  -> fresh path-private database snapshots and coherence validation
  -> exact no-follow stat plus MediaFile logical snapshots
  -> immutable four-field plans for every file
  -> command-wide database/stat preflight
  -> same-directory complete candidate copy
  -> write and reopen/verify four fields plus unrelated tags and filesystem metadata
  -> rollback backup, os.replace, and replaced-source verification
  -> fixed-column mtime savepoint and fresh verification
  -> post-success write/database_change events
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
