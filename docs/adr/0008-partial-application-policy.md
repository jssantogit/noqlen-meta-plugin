# ADR 0008: Allow explicitly configured safe partial application

- Status: Accepted
- Date: 2026-07-26

## Context

Block 011 established a strict selected-release boundary after `BeetsTargetPlan`. Strict application
correctly applies nothing when any resolver review or target mapping blocker exists. Users may also
want independently safe mapped changes without weakening resolver, mapping, or application safety.

## Decision

- Strict remains the default application mode; partial mode requires explicit configuration.
- Strict blocks the entire application when any resolution `REVIEW` or mapping blocker exists.
- Partial mode may apply only `BeetsTargetPlan.mapped_changes`.
- Resolution reviews are withheld and never selected automatically.
- Mapping blockers are withheld and never reduced or serialized.
- Withheld fields remain visible in the plan and preview.
- Partial mode is plan classification, not per-field error recovery.
- All mapped changes remain one atomic, fully prevalidated subset.
- Stale mapped state or any application contract failure aborts the mapped subset before mutation.
- Canonical target-plan integrity remains mandatory in every mode.
- Only mapped mutation targets receive stale-state checks; withheld fields gain no new stale contract.
- Successful selected-info mutation invalidates `raw_data` and `item_data` caches.
- Noqlen mutates only selected `AlbumInfo` and never invokes downstream beets application itself.
- Downstream Item, library, file, and tag persistence remains normal beets behavior.
- Provider, capability, resolver, `ChangePlan`, mapping, and provider-failure semantics do not change.

## Consequences

Partial mode can produce a truthful mixed outcome: mapped changes are applied together while reviews
and blockers remain withheld. It cannot make an invalid plan writable, recover field-by-field from
application errors, or hide unresolved data. Strict callers and configurations retain Block 011
behavior by default.
