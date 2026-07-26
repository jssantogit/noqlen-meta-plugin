# Requirements - Strict Library Database Application

## Goal

Add explicit, strict, database-only application to the existing library command.

## Requirements

- Keep preview as the default and make `--apply` the sole CLI write permission.
- Evaluate resolver reviews and mapping blockers strictly per Album.
- Plan all selected Albums before the first write.
- Revalidate target-plan integrity, local Album cleanliness, planned current state from a fresh
  persisted Album snapshot, target values, and target uniqueness before mutation.
- Mutate only mapped Album fields and persist once with `Album.store(inherit=True)`.
- Let normal beets behavior inherit fields to Item database rows without direct Item orchestration.
- Perform no physical tag, path, art, or file operation.
- Abort later Album writes after an unexpected application or store failure.

## Out Of Scope

Partial CLI application, Item media mapping, direct Item persistence, tag synchronization, file
moves, art changes, interactive confirmation, and command-wide rollback.
