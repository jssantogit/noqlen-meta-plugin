# ADR 0022: Library identity audit and repair

- Status: Accepted
- Date: 2026-07-31

## Context

Block 025 repairs only selected importer metadata. Block 026 needs a separately authorized way to
audit and repair identities already persisted in a beets 2.12.x library without writing tags or
files. Block 024 remains the sole scoring, assignment, selection, verdict, and repair-readiness
engine.

Compatibility testing confirms that beets 2.12.x `Transaction.__exit__` commits a root transaction
even when its block exits by exception and does not automatically call rollback. Nested beets
transactions are not SQLite savepoints.

## Decision

1. Library identity is the explicit `--identity` mode on the existing `noqlenmeta` command and `nm`
   alias. No second command or alias exists.
2. Only the exact mode-local combination `--identity --apply` authorizes library identity repair.
   Bare `nm --apply` remains ordinary enrichment. Top-level enrichment settings, importer
   `identity.enabled`, `identity.preview`, `identity.apply`, provider settings, Field Authority,
   resolver, and `ChangePlan` neither grant nor suppress library identity work.
3. `--identity` and `--partial` are mutually exclusive. Identity has no partial or `--force` mode.
4. Positional arguments are a normal Item query in identity mode. A matched album Item expands to
   its complete persisted Album; matched Albums are deduplicated. Standalone Items become singleton
   targets. `--all` selects every Album and singleton exactly once.
5. Targets are ordered by Album database ID and then singleton Item database ID. Album Items use
   positive disc, positive track, then Item ID order. Paths are never keys or output.
6. Planning always starts with fresh Album and Item rows. The immutable selected boundary uses
   `library-item:<Item.id>` internally and validates exact supported beets model types and positive
   persisted IDs.
7. An immutable exact, path-free snapshot preserves the types and values of every structural,
   identity, mapping, membership, and ordering input. It is separate from the normalized Block 024
   context and supplies stale protection.
8. Album structure comes from `Album.albumartist`, `Album.album`, and every complete Album Item.
   Track artist may fall back to album artist. Flattened ordinal indexes exist only when all disc and
   track positions are positive and unique. Singleton structure comes from Item artist/title, with
   Item album falling back to title.
9. Album release and release-group identity aggregates the Album row first and every Item row in
   deterministic order. Mixed missing positions use private invalid markers. Malformed and mixed
   state remains auditable but markers never score, enter exact fetches, map, apply, or render.
   Per-track IDs always come directly from each Item.
10. Existing IDs remain comparison-only evidence. Block 024 scoring and global assignment are reused
    unchanged. One complete Album or singleton makes one call through the plugin's retained source.
11. Mapping is immutable and deterministic. Release and release-group IDs target every differing
    Album and Item copy for Albums, and the Item for singletons. Recording and release-track IDs
    target the assigned Items. Already-correct copies are omitted.
12. Ambiguous, confirmed, and non-repair-ready results map no writes. Repair-ready missing/conflict
    results map every differing required copy. Unknown fields, scopes, rows, malformed targets, or
    duplicate database targets are hard mapping errors; there is no partial identity mode.
13. Every context, source call, audit, and mapping completes before the first write. A command-wide
    fresh exact-snapshot preflight follows planning. Each eligible target receives another fresh
    exact-snapshot guard after acquiring its root beets transaction and before creating the
    savepoint. This closes membership and structural races after command-wide preflight. No source
    work occurs after writes begin.
14. Application recomputes the canonical plan and validates all changes before database mutation.
    Planning model objects remain unchanged.
15. One complete Album plus all changed Items, or one singleton Item, is updated under one named
    SQLite `SAVEPOINT` inside `Library.transaction()`.
16. Identity SQL uses only public `Transaction.mutate`, `mutate_many`, and `query`, fixed `albums` and
    `items` table/column identifiers, integer IDs, and bound values. Album rows accept only
    `mb_albumid` and `mb_releasegroupid`; Item rows accept the four fixed identity columns. No model
    `store()`, private connection/transaction-stack access, inserts, deletes, or flexible attributes
    participate in the write unit.
17. Every changed row is queried and exactly verified before `RELEASE SAVEPOINT`. Ordinary failures
    execute `ROLLBACK TO SAVEPOINT` and `RELEASE SAVEPOINT`, then raise a safe application error.
    Failure of SQLite rollback itself is integrity-critical. There are no compensating writes.
18. After successful root commit, every changed row is freshly re-fetched and verified. Only then is
    one deterministic public `database_change` event emitted per changed row. Notification failure
    reports that the database committed and never retries writes or implies rollback.
19. Identity mode always renders a privacy-safe result. Source failures are sanitized per target and
    do not stop planning other targets. During apply mode, each completed target is rendered before
    the next target begins. A later failure preserves earlier committed and rendered results, marks
    the propagated safe error as committed when applicable, and never claims command-wide rollback.
    Internal mapping/application errors are not swallowed.
20. Application is database-only and never calls tag/file read, write, sync, move, MediaFile, or
    importer metadata application APIs. Block 027 owns explicit synchronization of confirmed
    database MBIDs to files.
21. AcoustID remains outside v1.0. The frozen roadmap is Block 027, Block 028, then STOP.

## Consequences

Users can audit complete Albums and standalone Items without changing data, and can explicitly
repair only the four persisted MusicBrainz identity columns. Database values may intentionally differ
from file tags until Block 027. The explicit SQLite savepoint provides truthful per-target rollback
despite beets 2.12.x root exception-commit behavior.
