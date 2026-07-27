# ADR 0011: Add safe partial library database application

- Status: Accepted
- Date: 2026-07-27

## Context

Strict CLI application correctly prevents every Noqlen database mutation for an Album when resolver
review or persistent-target mapping blockers exist. Users also need an explicit way to persist the
independently safe mapped subset without weakening the audited Block 014 application boundary.

## Decision

1. Strict remains the default CLI application mode.
2. Partial requires both `--apply` and `--partial`.
3. `--partial` without `--apply` is invalid.
4. Importer application configuration does not authorize or select CLI application mode.
5. Partial may persist only `LibraryTargetPlan.mapped_changes`.
6. Resolver `REVIEW` fields remain withheld.
7. Library mapping blockers remain withheld.
8. Withheld fields remain visible in preview.
9. Partial is classification before application, not per-field exception recovery.
10. All mapped changes remain one atomically validated subset per Album.
11. Canonical target-plan integrity remains mandatory.
12. The local dirty guard remains mandatory.
13. A fresh persisted Album snapshot remains mandatory for mapped before-state validation.
14. Stale mapped state aborts the whole mapped subset.
15. Malformed mapped data aborts the whole mapped subset.
16. Genre tuples materialize as fresh lists only at application; scalar values are not coerced.
17. A successful mapped subset calls `Album.store(inherit=True)` exactly once.
18. Normal beets Album-to-Item database inheritance remains authoritative.
19. No physical file-tag synchronization or other file operation occurs.
20. Media remains unsupported at Album level and is never written to Items.
21. Plan-all-before-write remains mandatory.
22. An application or store failure aborts later Albums.
23. No command-wide rollback exists.

## Consequences

Partial mode can truthfully report mapped fields as partially stored while preserving unresolved and
unrepresentable fields. It cannot make a forged plan writable, tolerate stale state, reduce a
singular-target blocker, auto-accept review, or continue after a database failure. Earlier successful
Album stores can remain committed if a later Album fails.
