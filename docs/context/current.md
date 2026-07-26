# Current Context

## Project

Noqlen Meta Plugin — universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

Use `tiny` by default and `standard` for non-trivial feature blocks. Use `full` only for architecture or milestone audits.

## Tool Mode

`none` until a block explicitly declares another mode.

## Active block

None. Project-foundation bootstrap is complete.

## Active spec

No active implementation spec. Foundation record: `docs/specs/001-project-foundation/`.

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`

## Allowed files

Defined per future block.

## Forbidden files

Defined per future block. Local agent/tool configuration and real user-library data are always forbidden unless a later explicit policy says otherwise.

## Non-goals

- Do not fork or patch beets core as part of the current project direction.
- Do not replace beets matching in the initial product scope.
- Do not implement providers without an active scoped block.
- Do not use a real music library in automated tests.

## Behavior budget

Zero product behavior changes until the next block is explicitly planned.

## Validation

Baseline repository validation:

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
```

## Done when

The next block is explicitly defined with scope, allowed files, validation, done criteria, and stop condition.

## Stop condition

Stop before implementation if the next block is not defined or requires an architectural decision that is not yet recorded.
