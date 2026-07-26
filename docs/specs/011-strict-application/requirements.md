# Requirements - Strict Selected-Release Application

## Goal

Provide the first explicit opt-in boundary that can enrich only the selected beets `AlbumInfo` and
then return control to the normal importer lifecycle.

## Requirements

- Add independent `preview` and `apply` settings with `apply: false` by default.
- Permit application only when the source has no reviews and target mapping has no blockers.
- Validate canonical target-plan integrity and selected metadata `before` values before mutation.
- Materialize every target, reject duplicate targets, and mutate only after all checks pass.
- Materialize genres as a fresh list and preserve validated scalar types.
- Invalidate `raw_data` and `item_data` after successful mutation.
- Return an immutable, truthful result and propagate internal application failures.
- Never invoke downstream beets apply, add, database, tag, or file operations.

## Out of scope

Partial application, review acceptance, blocker dropping, direct Item/Album mutation, persistence,
rollback frameworks, CLI, providers, and beets core changes.
