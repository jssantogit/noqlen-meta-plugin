# Requirements - Field Authority Resolver

## Goal

Convert current metadata and normalized provider candidates into deterministic, explainable field
decisions without mutating beets, files, databases, inputs, or candidates.

## Functional requirements

- Represent immutable field rules with enablement, ordered authority, minimum confidence, and
  preserve-existing behavior.
- Represent field and provider enablement independently with conservative unknown defaults.
- Select by field authority after provider, authority-list, and confidence eligibility checks.
- Return `KEEP`, `PROPOSE`, `REVIEW`, or `SKIP` decisions with selected candidate provenance and
  relevant alternatives.
- Review same-provider ambiguity and preserved existing-value conflicts.
- Preserve structured metadata values and deterministic output ordering.
- Provide initial authority vocabulary for Discogs fields and planned mood, lyrics, synced lyrics,
  and cover capabilities while enabling only the current Discogs slice by default.

## Non-goals

Metadata application, beets lifecycle changes, configuration migration, CLI commands, semantic field
merging, provider adapters, persistence, network access, and confidence calibration.
