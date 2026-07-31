# ADR 0023: Identity tag synchronization

- Status: Accepted
- Date: 2026-07-31

## Context

Block 026 can establish coherent MusicBrainz identity in the beets database but intentionally does
not update media files. Block 027 needs an independently authorized, privacy-safe synchronization
boundary that does not become another matcher or generic metadata writer.

## Decision

1. The existing `noqlenmeta` command and `nm` alias gain `--identity-tags`; no command or alias is
   added.
2. Only the exact CLI combination `--identity-tags --write` permits file replacement. `--apply` and
   every enrichment/importer setting grant no tag-write authority.
3. Ordinary, `--identity`, and `--identity-tags` modes are mutually exclusive. Identity-tag mode
   rejects `--apply` and `--partial`.
4. Positional arguments remain Item queries. Album matches expand to complete Albums, standalone
   Items are supported, and Block 026 target and Item ordering is reused. `--all` covers both kinds.
5. No provider, network, MusicBrainz source, audit, resolver, or enrichment path participates.
6. The current database is the source of truth. This block validates canonical internal coherence;
   it does not independently prove that an identity belongs to a MusicBrainz release.
7. Album and every Item copy of release and release-group identity must be present, canonical, and
   equal. Every Item also needs canonical recording and release-track identity.
8. Repeated recording IDs are permitted; repeated release-track IDs block the complete Album. No
   partial target synchronization exists.
9. Missing, conflicting, and malformed file values are intentionally replaced from the database.
   There is no preserve-existing policy or force flag.
10. The writable allowlist is exactly `mb_albumid`, `mb_releasegroupid`, `mb_trackid`, and
    `mb_releasetrackid`. MediaFile owns FLAC, ID3, MP4, Vorbis, and Opus mappings.
11. Unsupported/unreadable formats and empty or invalid persisted paths block before replacement.
    Paths, filenames, local keys, temporary names, raw malformed values, and raw
    operating-system/MediaFile errors remain private. A valid file in the same command may continue.
12. Symlinks, nonregular files, duplicate selected paths, and pre-existing hard-link sets are blocked.
13. An exact device/inode/mode/size/mtime/ctime/link-count fingerprint is an ordinary-concurrency
    stale guard. It does not claim protection from a malicious process capable of preserving every
    stat field.
14. Preview is the default and creates no candidate, backup, lock, recovery file, database write, or
    event.
15. Every selected database row, file fingerprint, and logical tag surface is planned, followed by a
    command-wide fresh preflight, before the first candidate is created.
16. The source is never saved in place. A random hidden, extension-preserving candidate is created in
    the source directory and populated with a metadata-preserving complete copy. Candidate and
    backup-copy fallback source reads use `O_NOATIME` and no-follow descriptors; ordinary path-based
    media copying is forbidden. Files without atime-safe copy support block before replacement.
17. Every candidate writes all four identity fields, even if one differs. It is reopened to verify
    canonical targets and every safely readable unrelated writable MediaFile field.
18. Permission mode, observable owner/group, and public extended attributes are compared. Failure to
    prove supported filesystem metadata preservation blocks replacement; ACL preservation is not
    claimed beyond observable public filesystem metadata.
19. A verified same-directory rollback backup exists before `os.replace()` changes the source path.
    Hard-link backup is preferred, with a verified complete-copy fallback.
20. The replaced source is freshly reopened and verified. Safe post-replacement failures restore and
    verify the original, including original mtime and a final link count of one in addition to full
    content, tags, and supported metadata; restoration failure is integrity-critical.
21. Only operational `items.mtime` may change in the database. A fixed-column named SQLite savepoint
    verifies the Item/target before update, checks the row, and fresh-verifies after commit. Identity
    database columns never change.
22. Beets' `write(item, path, tags)` event is a mutable pre-write hook and is intentionally not emitted
    by the immutable candidate workflow. `after_write(item, path)` followed by
    `database_change(lib, model)` occurs only after replaced-source verification, mtime commit, and
    fresh Item verification. No-op, preview, blocked, and restored attempts emit no event. Listener
    failure reports committed state and does not restore the committed file.
23. No-op files create no artifacts, database update, replacement, or event.
24. Expected pre-replacement blockers coexist with eligible files. Internal contract and
    integrity-critical failures are not swallowed.
25. Write-mode results render immediately in deterministic Item-ID order. A later failure may leave
    earlier per-file commits in place and is marked committed; no command-wide rollback is claimed.
26. Tiny committed FLAC, MP3, M4A, Ogg Vorbis, and Opus fixtures contain generated silence only and
    exercise real MediaFile round trips without runtime encoders or network access.
27. Application tracks source-unchanged, source-replaced, and mtime-committed phases explicitly. A
    safely rolled-back mtime failure restores the original. An integrity-critical uncertain mtime
    state reports `committed=True`, retains the original backup as a path-private recovery artifact,
    and never performs blind restoration. The finalizer does not delete a retained recovery backup.
28. Preview never claims candidate verification. Per-file capability is proven only by an actual
    `--write` candidate round trip.
29. Block 028 v1.0 Hardening and Release is next, then STOP.

## Consequences

Users can preview and explicitly synchronize confirmed database identity while unrelated tags remain
verified and source paths remain private. Atomicity is per file, with a rollback artifact protecting
the interval between source replacement and successful operational database bookkeeping.
