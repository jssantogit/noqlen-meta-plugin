# Current Context

## Project

Noqlen Meta Plugin — universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

Use `tiny` by default and `standard` for non-trivial feature blocks. Use `full` only for architecture or milestone audits.

## Tool Mode

`combo` for Block 003: OpenCode native capabilities, Serena for targeted symbol/navigation work,
and RTK for noisy shell commands.

## Active block

Block 003 - Discogs Album Enrichment Provider.

## Active spec

`docs/specs/003-discogs-provider/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`

## Allowed files

Discogs provider implementation, its optional dependency, focused fixtures/tests, ADR 0002, Block
003 specs, and context/handoff documents.

## Forbidden files

Block 002 contract redesign, resolver/authority behavior, persistence, beets hooks/configuration,
OAuth, caching, Master Release lookup, other providers, unrelated files, local tool configuration,
and real user-library data.

## Non-goals

- Do not fork or patch beets core as part of the current project direction.
- Do not replace beets matching in the initial product scope.
- Do not expand the provider into beets lifecycle or resolver behavior.
- Do not use a real music library in automated tests.

## Behavior budget

One synchronous production Discogs adapter may perform direct release lookup or one bounded search
and concrete release fetch. It only returns normalized candidates and performs no writes.

## Validation

Baseline repository validation:

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
```

## Done when

The production provider, optional dependency/ADR, fixture-backed tests, specs, and handoff are
committed after baseline validation passes.

## Stop condition

Stop after Block 003. Do not begin beets lifecycle integration, resolver behavior, or another
provider.
