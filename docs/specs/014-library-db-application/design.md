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
stale checks, fully prevalidates the mapped subset, assigns only mapped targets, and calls
`Album.store(inherit=True)` exactly once when changes exist.

Each Album store owns its normal beets transaction. No transaction spans provider calls or multiple
Albums. Rendering always distinguishes preview, blocked, stored, and no-change outcomes and states
that file tags are unchanged.
