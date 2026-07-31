# Block 026 Design

## Flow

```text
validate identity CLI
  -> Item query / --all
  -> complete fresh Albums + standalone Items
  -> immutable exact snapshots and Block 024 contexts
  -> retained MusicBrainz source, audit every target
  -> immutable canonical database plans
  -> command-wide stale preflight
  -> optional root transaction, final full-target stale guard, then SQLite SAVEPOINT application
  -> in-savepoint verification, root commit, fresh verification, events
  -> privacy-safe preview/result for every target
```

## Modules

- `identity/library.py`: selection, fresh immutable boundaries, exact snapshots, contexts, audit.
- `identity/library_mapping.py`: fixed-column deterministic database target plans.
- `identity/library_application.py`: plan integrity, stale guards, savepoint SQL, verification, events.
- `identity/library_preview.py`: path/key/marker/error-safe rendering.
- Plugin entry point: one parser flag and exclusive mode branch; ordinary path remains unchanged.

The exact snapshot retains raw types/values separately from normalized audit data. Album Items are
ordered by positive disc, positive track, and Item ID. Local keys use Item IDs internally but are
never displayed. Mapping order is deterministic by target and Item order; already-correct canonical
copies do not become writes.

Preview-only mode renders after planning and opens no database transaction. Apply mode first finishes
the unchanged command-wide preflight, then applies and renders each prepared record in deterministic
order. If a later target fails, already rendered changes remain committed. The propagated safe error
is annotated with `committed=True` only when an earlier result actually applied database changes;
confirmed no-ops, blocked, and unavailable records do not count.

## Persistence

beets 2.12.x commits root transactions on exceptional context exit, so application never relies on
exception unwinding. Application first acquires the per-target root transaction, rebuilds and compares
the complete fresh structural/membership/identity snapshot inside it, and only then opens the
fixed-name SQLite savepoint through `Transaction.mutate`. A stale failure before the savepoint has no
mutation to roll back. After savepoint creation, application performs only bound fixed-column
`UPDATE`s, queries every changed row through the same transaction, and releases only after exact
verification. Failures roll back to and release the savepoint before a safe error escapes. A rollback
failure is integrity-critical.

No `Album.store()`, `Item.store()`, private connection, manual commit/rollback, or model mutation is
used. Fresh post-commit models are verified and then delivered via `database_change`. Event failure
cannot reverse or retry committed SQL. No tags or physical files are touched.
