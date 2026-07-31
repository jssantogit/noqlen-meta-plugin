# Block 026 Requirements

## Goal

Add a dedicated, always-previewed `--identity` mode to existing `noqlenmeta`/`nm` that audits
persisted MusicBrainz identity and optionally repairs only the beets database with
`--identity --apply`.

## Behavior

- Keep one command and alias. Ordinary behavior is unchanged without `--identity`.
- Require an Item query or `--all`; reject query plus `--all` and `--identity --partial`.
- Expand matched album Items to complete Albums, deduplicate Albums, support standalone Items, and
  order Albums then singletons by persisted ID.
- Use fresh exact path-free snapshots and immutable selected boundaries before Block 024 context
  construction. Unsafe/incomplete structure makes a target unavailable without a source call.
- Aggregate Album and Item copies of release identity, preserve mixed/malformed state privately, and
  consume Block 024 scoring, assignment, verdict, and repair readiness unchanged.
- Retain one injectable source and make one source call per complete target. Sanitize source failures
  and continue planning other targets.
- Map repair-ready missing/conflict findings to every differing required fixed database copy. Map no
  writes for confirmed, ambiguous, or non-ready results.
- Complete all context, source, audit, and mapping work before writing. Perform command-wide and
  per-target exact stale guards. Create the real SQLite savepoint before rebuilding the final
  pre-write complete snapshot.
- Recompute and validate the canonical plan before applying one target under one real SQLite
  savepoint using public transaction SQL methods and bound values.
- Before releasing the savepoint, rebuild the complete target and require exact equality to a pure
  expected-post snapshot derived only from the original snapshot plus canonical planned identity
  changes. Structural, membership, and unplanned identity changes must roll back.
- Verify rows before savepoint release and after root commit. Emit one post-commit
  `database_change` event per changed row.
- Never call model stores, importer application, tag/file APIs, private database connections, or
  compensating writes.
- Always render privacy-safe results with database-only wording. In apply mode, render each completed
  target immediately. If a later target fails, retain earlier results and mark the safe propagated
  error when earlier database changes committed without claiming command-wide rollback.

## Permission Matrix

| Invocation/configuration | Result |
| --- | --- |
| `nm --apply QUERY` | Ordinary enrichment only |
| importer `identity.apply: true` | Importer selected-metadata repair only |
| `nm --identity QUERY` | Library identity audit only |
| `nm --identity --apply QUERY` | Library identity database repair |

Block 027 owns tag synchronization. The remaining roadmap is 027, 028, STOP.
