# Current Context

## Project

Noqlen Meta Plugin — universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

Use `tiny` by default and `standard` for non-trivial feature blocks. Use `full` only for architecture or milestone audits.

## Tool Mode

`combo` for Block 002: OpenCode native capabilities, Serena for targeted symbol/navigation work,
and RTK for noisy shell commands.

## Active block

None. Block 002 - Metadata Domain Model + Provider Contract is complete and validated; it is closed
by commit `feat: add metadata domain and provider contract`.

## Active spec

`docs/specs/002-metadata-domain-provider-contract/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`

## Allowed files

Block 002 was limited to domain/provider contract modules, focused tests, its spec, and context
handoff documents.

## Forbidden files

Concrete providers, resolver/authority behavior, persistence, beets hooks, unrelated project files,
local agent/tool configuration, and real user-library data.

## Non-goals

- Do not fork or patch beets core as part of the current project direction.
- Do not replace beets matching in the initial product scope.
- Do not implement providers without an active scoped block.
- Do not use a real music library in automated tests.

## Behavior budget

The package now defines inert production contracts only. It performs no enrichment or network I/O.

## Validation

Baseline repository validation:

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
```

## Done when

The immutable release context, validated metadata candidate, provider protocol, provider error,
focused tests, specs, and handoff are committed after baseline validation passes.

## Stop condition

Stop after Block 002. Do not begin a concrete provider until Block 003 is explicitly scoped.
