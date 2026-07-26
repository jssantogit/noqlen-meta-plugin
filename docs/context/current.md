# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 008 because it formalizes the provider contract across policy, adapters, and the
beets import lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 008 - Provider Capabilities and Orchestration Contract.

## Active spec

`docs/specs/008-provider-capabilities/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`

## Allowed files

Dependency-light provider specs, narrow orchestration helpers, provider contracts, minimal built-in
provider/integration/resolver changes, focused tests, README, ADR 0004, Block 008 specs, and
context/handoff documents.

## Forbidden files

Candidate application, beets/file/database mutation, CLI, semantic field merging, persistence,
dynamic provider discovery, caching, concurrency, network behavior changes, additional providers,
advanced policy YAML, ChangePlan, and beets core.

## Behavior budget

Discogs and iTunes are invoked only when enabled fields, Field Authority, and immutable adapter
capabilities intersect. Candidate output is contract-validated, expected service failures remain
isolated, and one resolver pass produces preview decisions that are never applied.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Authority and capability remain independent, specs match real adapter output, irrelevant providers do
no work, contract defects remain visible, optional Discogs loading stays lazy, existing two-provider
resolution is unchanged, and baseline validation is green.

## Stop condition

Stop after Block 008. Do not begin ChangePlan, apply decisions, or add metadata writes, providers,
lyrics, artwork, or CLI.
