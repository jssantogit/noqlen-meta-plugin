# Design - Strict Selected-Release Application

## Boundary

```text
ChangePlan -> BeetsTargetPlan -> strict gate -> selected AlbumInfo -> normal beets lifecycle
```

`apply_beets_target_plan()` is the only production mutation function. It validates input contracts,
recomputes the canonical target plan, returns blocked before mutation when reviews or blockers exist,
compares current canonical values with planned `before` values, materializes all values, checks target
uniqueness, mutates the selected info, and invalidates only `raw_data` and `item_data`.

The listener never calls downstream beets lifecycle methods. Running at `import_task_choice` means
enriched info is visible to later duplicate resolution. Current targets do not alter the default
`albumartist album` duplicate identity, but configured custom keys may observe enrichment.
