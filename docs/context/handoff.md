# Handoff

## State

Block 014 adds explicit strict database application to the existing `noqlenmeta` Subcommand and `nm`
alias. Preview remains default. `--apply` plans every selected Album first, then independently gates
and persists eligible mapped changes through `Album.store(inherit=True)`.

## Completed

- `--apply` is the only CLI database write permission and is independent from importer settings.
- Missing query/`--all` intent still fails before providers, library queries, or writes.
- All selected Albums are planned before the first database mutation.
- Strict review and mapping-blocker policy is evaluated independently per Album.
- Target-plan integrity, clean Album state, stale mapped values, target materialization, and target
  uniqueness are checked before assignment.
- Genre tuples become fresh lists; scalar values are validated without coercion.
- Only mapped Album fields are assigned, then `Album.store(inherit=True)` is called once.
- Normal beets storage propagates inheritable Album fields to Item database rows.
- Preview/application output truthfully states that physical file tags are unchanged.
- Unexpected application or store errors propagate and stop later Albums.
- In-memory tests cover persistence, inheritance, forbidden file operations, planning order, and
  per-Album failure behavior.

## Important decisions

- The first CLI write policy is strict only; no resolver review or mapping blocker is accepted.
- Persistent application has its own boundary and does not reuse importer `AlbumInfo` application.
- Beets owns Item inheritance and per-Album database transaction behavior.
- Database application does not imply file-tag synchronization.
- There is no command-wide transaction or rollback across Albums.
- Media remains unsupported and blocking.

## Deferred

- Safe partial CLI application.
- Optional, separately authorized physical tag synchronization.
- Media mapping, provenance persistence, confidence calibration, artwork, lyrics, and providers.

## Recommended next block

After independent Block 014 review, a later block may design safe partial library database
application. Physical tag synchronization must remain a separate permission boundary and should not
be combined with that policy change.
