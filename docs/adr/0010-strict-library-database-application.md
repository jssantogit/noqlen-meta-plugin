# ADR 0010: Add strict library database application

- Status: Accepted
- Date: 2026-07-26

## Context

The library CLI already produces an audited `LibraryTargetPlan` for each persistent Album. The first
write boundary must preserve that mapping policy, avoid unrelated dirty metadata, protect against
stale plans, use normal beets persistence, and distinguish database updates from physical tag writes.

## Decision

1. `--apply` is the only CLI write permission; without it, `beet nm` remains read-only.
2. Importer `apply` and `apply_mode` configuration does not authorize CLI writes.
3. The first CLI write policy is strict only and is evaluated independently per Album.
4. Any resolver `REVIEW` blocks that Album.
5. Any `LibraryMappingBlocker` blocks that Album.
6. Only `LibraryTargetPlan.mapped_changes` may mutate persistent Album metadata.
7. The target plan must equal a fresh canonical mapping of its source before mutation.
8. Immediately before mutation, Album mapped values from a fresh database snapshot must still match
   each planned `before` value; the Album object retained from planning is not trusted for this check.
9. The Album must have no pre-existing dirty metadata before Noqlen mutation.
10. Every target value is validated and materialized before any assignment.
11. Duplicate persistent targets are rejected before mutation.
12. Immutable genre tuples become fresh lists only at application; scalar values are not coerced.
13. Persistence calls exactly `Album.store(inherit=True)` once when changes exist.
14. Noqlen does not manually assign or store Items.
15. Normal beets Album storage propagates inheritable fields to Item database rows.
16. This boundary writes database metadata only; it performs no tag, move, art, or file operation.
17. `media` remains unsupported and blocking.
18. Every selected Album is planned before the first database write.
19. Expected provider failures remain fail-open during planning; internal planning errors propagate
    before application begins.
20. Each Album uses normal beets transaction behavior; provider work is outside transactions.
21. There is no command-wide multi-album rollback.
22. An unexpected application or store failure aborts later Album writes.
23. A plan with no reviews, blockers, or mapped changes is a successful no-op and is not stored.
24. Safe partial CLI application is deferred to a separately reviewed block.

If the fresh lookup shows that the Album no longer exists, application fails with a
`LibraryApplicationError`. Other database errors propagate unchanged.

## Consequences

An explicit command may leave database metadata richer than physical file tags. Safe and blocked
Albums in one query proceed independently, but successful earlier stores remain committed if a later
Album fails. The plan-all phase reduces avoidable partial-command failures without holding network
work or multiple Album writes in one transaction.
