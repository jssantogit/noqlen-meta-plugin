# Safety Model

You will understand the safeguards behind each explicit mutation boundary.

## Separate Authorities

Preview is the default. Importer `apply`, library `--apply`, identity
`--identity --apply`, native `beet write`, and identity-tag
`--identity-tags --write` are separate permissions. None silently grants
another. Noqlen has no `--force`.

## Planning And Database Guards

Noqlen collects and maps all selected command targets before the first write.
Application checks immutable plans against fresh target state to detect stale
data, changed shape, duplicate targets, and invalid mappings.

Ordinary Albums commit independently through normal beets storage. Identity
database repair uses one real SQLite SAVEPOINT per complete Album-plus-Items or
singleton target. There is no command-wide rollback claim; a later failure can
leave an earlier reported target committed.

## Identity-Tag File Workflow

The source is never saved in place. For each eligible file Noqlen:

1. captures an exact database and source snapshot without displaying the path;
2. requires a regular single-link source and atime-safe no-follow reads;
3. creates an extension-preserving candidate in the same directory;
4. writes and round-trip verifies all four MBID tags;
5. verifies unrelated logical tags and supported filesystem metadata;
6. creates a same-directory rollback backup;
7. atomically replaces the source with `os.replace`;
8. reopens and verifies the replaced file;
9. updates only operational Item `mtime` under a fixed-column SAVEPOINT;
10. emits normal post-success events and removes safe temporary artifacts.

Preview creates no candidate or backup, so it cannot prove write capability
for a particular file. `--write` proves capability through the real candidate
round trip before replacement.

`O_NOATIME` and `O_NOFOLLOW` prevent an unsafe fallback read from silently
changing source access time or following a symlink. If those guarantees,
metadata preservation, hard-link rules, or atomic same-directory replacement
cannot be proven, the file blocks before replacement.

## Restoration And Uncertain State

Files commit independently. A safely reversible failure restores and verifies
the original. If replacement or database bookkeeping reaches an uncertain
committed state, Noqlen reports it truthfully, stops later work, and retains a
path-private original backup rather than blindly restoring or deleting it.
Listener failure after a verified commit does not roll back a correct file.

Private paths, temporary names, raw malformed IDs, raw lyrics, and raw provider
errors are excluded from normal preview and warning output.
