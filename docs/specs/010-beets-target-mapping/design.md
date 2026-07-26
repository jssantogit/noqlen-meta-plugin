# Design - Read-Only Beets Target Mapping

## Boundary

```text
MetadataCandidate[] -> FieldDecision[] -> ChangePlan -> BeetsTargetPlan -> read-only preview
```

`map_change_plan_to_beets()` is a pure post-resolution translation against one immutable built-in
target table. It does not require an `AlbumInfo` instance.

## Rules

`genres` remains a tuple in the target plan even though a future beets mutation would require a list.
`country` requires a string and `year` requires a non-boolean integer from 1 through 9999. Canonical
tuples for style, label, catalog number, barcode, and media map only when their length is exactly one.
Longer tuples become blockers; malformed shapes raise `BeetsMappingError`. Missing registrations,
including `format_descriptions`, become unsupported-target blockers.

Mapped changes and blockers retain their original `PlannedChange`; target-shaped history and
duplicated provenance are not introduced.
