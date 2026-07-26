# Design - Strict Library Database Application

## Flow

```text
query validation
  -> query persistent Albums
  -> plan every usable Album through shared planning and LibraryTargetPlan mapping
  -> for each prepared plan: strict application gate, optional Album mutation/store, render result
```

`LibraryAlbumPlan` is a small immutable command holder for the plan-all/apply-render phase split.
`apply_library_target_plan()` is the only new production function permitted to mutate persistent
library metadata. It reconstructs the canonical mapping, returns a blocked result before dirty or
stale checks, rejects local dirty state, and then fetches a fresh Album from the database. Planned
mapped `before` values are compared with that fresh snapshot rather than the Album retained from
planning. After full prevalidation, assignments and `Album.store(inherit=True)` still use the
original selected Album object. A missing row becomes `LibraryApplicationError`; unrelated database
errors propagate.

Each Album store owns its normal beets transaction. No transaction spans provider calls or multiple
Albums. Rendering always distinguishes preview, blocked, stored, and no-change outcomes and states
that file tags are unchanged.
