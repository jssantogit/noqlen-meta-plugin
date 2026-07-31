# Block 027 Requirements

## Goal

Add explicit preview-first synchronization of the four canonical MusicBrainz identity values from
the beets database to selected media files.

## Required behavior

- Keep one `noqlenmeta`/`nm` command. Add exclusive `--identity-tags` mode and mode-local `--write`.
- Require an Item query or `--all`; expand Album matches completely and support standalone Items.
- Perform no provider, source, audit, resolver, matching, enrichment, import, or identity repair work.
- Require complete canonical coherent database identity before reading/writing a target's tags.
- Snapshot fresh database rows, exact file stat identity, four current fields, and every safely
  readable unrelated writable MediaFile field.
- Preview every file without creating artifacts, writing files/database, or emitting events.
- Treat empty or invalid persisted paths as expected blocked outcomes without filesystem access or
  preventing another valid selected file from proceeding.
- Complete all planning and command-wide preflight before the first candidate.
- Reject symlinks, nonregular files, duplicate paths, hard-linked sources, stale files/database rows,
  unsupported formats, and unprovable metadata preservation.
- Write all four fields through a same-directory candidate, verify the candidate, create a rollback
  backup, atomically replace the source, and verify the replaced source.
- Restore the original on a safely classified post-replacement failure. For uncertain mtime commit
  state, report committed and integrity-critical, retain the path-private original backup, and do not
  restore blindly.
- Update only operational Item `mtime` with fixed SQL under a real savepoint, then emit
  `after_write(item, path)` and `database_change(lib, model)`. Never emit the mutable pre-write
  `write(item, path, tags)` hook.
- Report candidate capability as verified only after the specific file completes a candidate round
  trip; preview must state that `--write` verification is still required.
- Render privacy-safe per-file results immediately; report truthful committed state on later failure.

## Exclusions

No new command, force/in-place/partial mode, provider call, MusicBrainz lookup, identity inference,
database identity repair, generic tag writing, nonidentity metadata write, source path display,
symlink following, user-library test, runtime encoder, or command-wide rollback claim.
