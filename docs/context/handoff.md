# Handoff

## State

Block 009 inserts an immutable, provider-independent, target-independent `ChangePlan` after the
existing Field Authority resolver. The real import flow translates decisions into a plan and renders a
plan-oriented preview while selected import state remains unchanged.

## Completed

- `PROPOSE` becomes one immutable `PlannedChange` with before/after values, resolver reason, and the
  selected candidate as structured provenance.
- `REVIEW` is an explicit blocker; `KEEP` and `SKIP` create no changes but remain visible.
- Plan categories are deterministic and duplicate or inconsistent decisions raise `ChangePlanError`.
- Canonical tuple and scalar values remain structured until presentation.
- The plan preview reports category counts and conflict status with sanitized details.
- Existing providers, authority, confidence, failure isolation, one resolver pass, and read-only import
  snapshots remain unchanged.

## Important decisions

- `FieldDecision` owns metadata choice; `ChangePlan` describes consequences without choosing again.
- Conflict-free means no review blockers, not writable or approved for application.
- Candidate provenance is retained by structure and is not persisted.
- Beets field mapping and multi-value serialization require a separate architectural decision.
- No metadata, database, tags, files, plans, or provenance are written.

## Deferred

- Beets application mapping, metadata application, provenance persistence, and field-specific merge
  policy.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

After independent Block 009 review, Block 010 should explicitly design canonical Noqlen field to
beets target mapping, including lossless or lossy rules for multi-value fields. Do not implement writes
without that separate reviewed policy.
