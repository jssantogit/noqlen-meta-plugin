# Requirements - Read-Only ChangePlan

## Goal

Translate immutable `FieldDecision` values into deterministic, target-independent metadata
consequences used by the real read-only preview flow.

## Requirements

- Represent each `PROPOSE` as one immutable `PlannedChange` with before/after values, source candidate,
  and resolver reason.
- Retain `REVIEW`, `KEEP`, and `SKIP` decisions in separate immutable plan categories.
- Preserve candidate provenance and canonical scalar or tuple value shapes.
- Reject missing selections, duplicate fields, and candidate field/value inconsistencies as internal
  `ChangePlanError` defects.
- Sort each category by canonical field and expose truthful change/review/conflict properties.
- Build and render the plan in the import path without changing providers, resolution, or import state.

## Out of scope

Beets target mapping, serialization, metadata application, persistence, configuration, CLI, provider
changes, and partial-application policy are excluded.
