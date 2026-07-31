# Block 026 Review

## Scope

The existing `noqlenmeta`/`nm` command now has a separate `--identity` mode. Item queries expand to
complete Albums and standalone singleton targets. Preview is always rendered. Only
`--identity --apply` can update the four fixed identity columns in the beets database.

## Safety

- Block 024 is reused unchanged and existing IDs remain comparison-only.
- Planning uses fresh rows and immutable exact path-free stale snapshots.
- All source/audit/mapping work and command-wide preflight precede writes.
- Album and Item changes share one named real SQLite savepoint per target.
- SQL uses public transaction methods, fixed identifiers, and bound values.
- In-savepoint and fresh post-commit verification are mandatory.
- Events occur only after successful commit and verification.
- Ambiguous, confirmed, unavailable, and non-ready outcomes do not write.
- No model store, file/tag, private connection, or compensation path exists.

## Compatibility

A real temporary beets 2.12.x database regression proves exceptional root transaction exit commits,
while explicit rollback to the Block 026 savepoint restores all target identity columns after an
injected mid-target failure.

## Roadmap

Block 027 will explicitly synchronize confirmed database identity to tags. Block 028 hardens and
releases v1.0. Then STOP.
