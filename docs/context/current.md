# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 019 because it adds one domain/integration boundary and provider scope while
leaving resolver, mapping, application, and execution behavior unchanged.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 019 - Track-Level Enrichment Foundation.

## Active spec

`docs/specs/019-track-enrichment-foundation/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0013-configurable-resolution-policy.md`
- `docs/adr/0014-lastfm-community-genre-enrichment.md`
- `docs/adr/0015-track-enrichment-boundary.md`

## Allowed files

Track domain and read-only integration, provider contracts/spec scope, release availability gate,
focused tests, README, ADR 0015, Block 019 specs, and context/handoff documents.

## Forbidden files

Track providers, network calls, track matching, resolver/planner duplication, target mapping,
application or persistence, fingerprints, cache, concurrency, CLI flags, and physical files.

## Behavior budget

Track identity and provider scope may be represented read-only. Existing release provider results,
album CLI behavior, authority, mapping, application, persistence, and file semantics remain unchanged.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Track identity/adapters and scoped provider contracts are validated and documented, current providers
remain release-scoped, the track registry is empty, and all offline validation passes.

## Stop condition

Stop after Block 019. Do not add LRCLIB, track execution, target mapping, or application.
