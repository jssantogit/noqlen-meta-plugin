# Handoff

## State

The repository foundation is ready for scoped development.

The project is an external beets plugin named `noqlenmeta`. Beets remains responsible for candidate matching and import flow. Noqlen Meta is intended to enrich the selected release by gathering field-level candidates from multiple providers, resolving those candidates according to authority/confidence policy, preserving provenance, and exposing reviewable changes before eventual writes.

## Completed

- Repository identity and project direction documented.
- External beets plugin package scaffolded under `beetsplug/noqlenmeta`.
- Python packaging and baseline development dependencies defined.
- Noqlen Playbook agent contract added.
- Real-first, fixture-backed provider policy documented.
- Initial architecture decision recorded.
- Baseline CI, lint, test, and contamination checks defined.

## Important decisions

- Prefer an external beets plugin over a beets fork.
- Do not replace the beets matcher in the initial scope.
- Treat provider integration as enrichment after release identification.
- Implement real production adapters directly; use sanitized fixtures for deterministic default tests.
- Keep live network tests opt-in.
- Never use real music-library data in automated tests.

## Not implemented

- Metadata schema.
- Provider protocol.
- Provider adapters.
- Field authority.
- Confidence model.
- Resolver.
- Provenance storage.
- Import hooks or enrichment commands.
- Dry-run/review user experience.

## Recommended next block

Define the **metadata domain model and provider contract** before implementing a concrete provider. Keep that block production-oriented: define only contracts needed by the first real vertical slice and avoid building a parallel fake-provider framework.

Suggested context: `standard`.

Suggested outputs:

- active spec for metadata candidate/domain contracts;
- minimal production data structures;
- provider boundary/protocol;
- focused unit tests with synthetic values;
- updated handoff.
