# Handoff

## State

Block 015 extends the existing `noqlenmeta` Subcommand and `nm` alias with explicit safe partial
database application. Preview remains default, `--apply` remains strict, and only
`--apply --partial` permits a mapped subset to persist while unresolved or unrepresentable fields are
withheld.

## Completed

- `--partial` exists on the single command and raises `ui.UserError` without `--apply` before provider
  or library work.
- CLI mode is invocation-only and remains independent from importer `apply` and `apply_mode`.
- Strict behavior remains the default and unchanged.
- Partial mode persists only `LibraryTargetPlan.mapped_changes`; reviews and mapping blockers remain
  unchanged and visible.
- A partial plan with only withheld fields is a valid no-store outcome.
- Target integrity, local dirty state, fresh database stale checks, materialization, and uniqueness
  remain mandatory for the mapped subset.
- Mapped changes are mutated only after full validation and stored once with
  `Album.store(inherit=True)`.
- Normal beets Item inheritance remains authoritative; no direct Item or physical file operation was
  added.
- All selected Albums are still planned before writes; application/store errors stop later Albums
  without rolling back earlier stores.

## Important decisions

- Strict remains the default CLI write policy.
- Partial is classification before application, never per-field exception recovery.
- Persistent application remains independent from importer `AlbumInfo` application policy.
- Beets owns Item inheritance and per-Album database transaction behavior.
- Database application does not imply file-tag synchronization.
- There is no command-wide transaction or rollback across Albums.
- Media remains unsupported: blocking in strict mode and withheld in partial mode.

## Deferred

- Optional, separately authorized physical tag synchronization.
- Media mapping, provenance persistence, confidence calibration, artwork, lyrics, and providers.

## Recommended next block

Stop after independent Block 015 audit and reassess product direction. Physical tag synchronization,
if selected later, must remain a separate explicit permission from database `--apply`.
