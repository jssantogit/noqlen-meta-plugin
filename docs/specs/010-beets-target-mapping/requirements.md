# Requirements - Read-Only Beets Target Mapping

## Goal

Analyze each canonical `PlannedChange` against the installed beets `AlbumInfo` contract without
rerunning resolution or mutating metadata.

## Requirements

- Define immutable target specifications for `genres`, `style`, `label`, `catalognum`, `barcode`,
  `country`, `year`, and `media` with their actual list or scalar shapes.
- Preserve tuple structure for `genres`; map one-value canonical tuples to singular targets.
- Block multi-value to singular conversion and unsupported canonical fields without discarding data.
- Raise `BeetsMappingError` for malformed canonical value shapes or invalid mapping definitions.
- Retain the source `ChangePlan`, original `PlannedChange`, and candidate provenance by identity.
- Produce deterministic immutable mapped and blocked categories.
- Route the real import preview through `BeetsTargetPlan` while leaving all import state unchanged.

## Out of scope

Mutation, metadata application, writes, delimiter serialization, custom fields, mapping
configuration, provider/resolver changes, persistence, CLI, and partial-application policy.
