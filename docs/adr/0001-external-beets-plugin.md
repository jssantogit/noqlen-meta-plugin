# ADR 0001: Build Noqlen Meta as an external beets enrichment plugin

- Status: Accepted
- Date: 2026-07-25

## Context

Noqlen Forge explored a broader music-library engine with richer multi-provider metadata, field authority, confidence, provenance, review, and safety concepts. Reimplementing beets' mature importer and matcher would duplicate substantial existing work.

The project needs a path that preserves beets' mature identification/import behavior while allowing Noqlen to substantially improve metadata completeness and field-level decision quality.

## Decision

Noqlen Meta will be developed as an external beets plugin in the `beetsplug.noqlenmeta` namespace.

In the initial product scope:

- beets remains responsible for candidate matching, release identification, and its normal import lifecycle;
- Noqlen Meta enriches an identified/selected release rather than replacing the matcher;
- provider-specific data is normalized into Noqlen-owned domain contracts;
- field authority, confidence, conflict resolution, provenance, and review belong to the Noqlen layer;
- changes to beets core are not required for the initial architecture and should be avoided unless a future proven limitation justifies a separate architectural decision.

## Consequences

### Positive

- Reuses beets' mature matching and importer instead of recreating them.
- Keeps upstream beets upgrades feasible.
- Allows Noqlen Meta to be installed independently by existing beets users.
- Focuses development effort on metadata completeness and decision quality.
- Keeps provider and resolver logic testable outside beets internals where practical.

### Costs and risks

- Plugin lifecycle hooks may constrain where enrichment can occur.
- Some desired fields may require explicit MediaFile field registration or format-specific storage policy.
- A future feature may reveal a genuine beets-core limitation; that must be demonstrated before considering a patch or fork.

## Alternatives considered

### Fork beets

Rejected for the initial project because it increases maintenance cost and upstream merge burden before a core patch has been shown to be necessary.

### Continue Noqlen Forge as a complete replacement

Not selected for this project because matching/import maturity would need to be rebuilt while the immediate product goal is richer metadata.
