# Design - Read-Only ChangePlan

## Boundary

```text
MetadataCandidate[] -> FieldDecision[] -> ChangePlan -> preview
```

The resolver remains the sole metadata decision-maker. `build_change_plan()` is a pure translation:
`PROPOSE` creates a change, `REVIEW` creates a blocker, and `KEEP`/`SKIP` remain visible without
creating changes.

## Contracts

`PlannedChange.source` retains the complete selected `MetadataCandidate`; provider metadata is not
duplicated. Plan categories are tuples sorted by field. Duplicate fields and inconsistent selected
candidates raise `ChangePlanError`, which is not handled as provider unavailability.

The preview formats structured values only for display. The plan contains no beets objects or target
field names and performs no I/O or mutation.
