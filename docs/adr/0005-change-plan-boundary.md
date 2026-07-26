# ADR 0005: Separate resolved decisions from metadata consequences

- Status: Accepted
- Date: 2026-07-26

## Context

`FieldDecision` already records the resolver's metadata choice. Future application needs an explicit,
reviewable description of those consequences without rerunning resolution or introducing beets target
semantics prematurely.

## Decision

- `FieldDecision` represents a resolved metadata choice.
- `ChangePlan` represents consequences and performs no new resolution.
- Only `PROPOSE` becomes a `PlannedChange`; `REVIEW` is an explicit blocker, while `KEEP` and `SKIP`
  produce no change.
- The plan remains canonical, provider-independent, and target-independent.
- Each planned change retains its selected candidate as structured provenance.
- Canonical multi-values remain structured rather than being formatted or reduced.
- Beets field mapping and serialization are deferred to a separate application-policy decision.
- Conflict-free means only that no review decision exists; it does not mean automatically writable.
- No metadata, database, tags, files, plans, or provenance are written or persisted in this block.

## Consequences

Plan previews can explain proposed changes and review blockers without querying providers again.
Duplicate or inconsistent resolved decisions fail as internal contract defects. Future application must
define explicit mappings for canonical multi-values before any write path is allowed.
