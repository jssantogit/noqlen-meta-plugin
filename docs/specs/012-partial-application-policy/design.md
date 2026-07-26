# Design - Safe Partial Application Policy

## Boundary

```text
BeetsTargetPlan -> strict|partial policy -> atomic mapped subset -> selected AlbumInfo
```

`BeetsApplicationMode` is parsed once when application is enabled. `STRICT` returns blocked before
mapped-state validation when reviews or blockers exist. `PARTIAL` retains their counts but continues
only with `mapped_changes`. Both modes first verify canonical target-plan integrity. Every eligible
change then passes stale-state validation, materialization, and unique-target validation before the
first mutation. Successful mutation invalidates only `raw_data` and `item_data`.

The immutable result distinguishes withheld fields, strict blocking, and mixed partial application.
Preview and silent-preview logs report the configured mode and outcome without implying downstream
writes.
