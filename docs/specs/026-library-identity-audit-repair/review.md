# Block 026 Review

## Scope

The existing `noqlenmeta`/`nm` command now has a separate `--identity` mode. Item queries expand to
complete Albums and standalone singleton targets. Preview is always rendered. Only
`--identity --apply` can update the four fixed identity columns in the beets database.

## Safety

- Block 024 is reused unchanged and existing IDs remain comparison-only.
- Planning uses fresh rows and immutable exact path-free stale snapshots.
- All source/audit/mapping work and command-wide preflight precede writes.
- The real SQLite savepoint is created before the final pre-write complete snapshot; the Python root
  lock alone is not treated as cross-connection isolation.
- Album and Item changes share one named real SQLite savepoint per target.
- SQL uses public transaction methods, fixed identifiers, and bound values.
- Row verification and a final complete expected-post snapshot occur before savepoint release; fresh
  post-commit verification remains mandatory.
- Events occur only after successful commit and verification.
- Ambiguous, confirmed, unavailable, and non-ready outcomes do not write.
- No model store, file/tag, private connection, or compensation path exists.
- Apply-mode targets render immediately after completion; later failures safely report whether earlier
  target changes committed and make no command-wide rollback claim.

## Compatibility

A real temporary beets 2.12.x database regression proves exceptional root transaction exit commits,
while explicit rollback to the Block 026 savepoint restores all target identity columns after an
injected mid-target failure.

Real boundary-race regressions move an Item and change track structure before application, and a
synchronized two-Library regression attempts a structural write after the in-savepoint pre-write
snapshot. It accepts only serialization/blocking or safe Noqlen rollback, never stale concurrent
success. Same-transaction structural, membership, and unplanned identity injections are rejected by
the final expected-post full snapshot and completely rolled back. Command regressions prove that an
earlier successful target is already rendered and remains committed when a later target races, while
a first-target race reports `committed=False`.

## Roadmap

Block 027 will explicitly synchronize confirmed database identity to tags. Block 028 hardens and
releases v1.0. Then STOP.
