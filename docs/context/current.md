# Current Context

## Project

Noqlen Meta Plugin — universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

Use `tiny` by default and `standard` for non-trivial feature blocks. Use `full` only for architecture or milestone audits.

## Tool Mode

`combo` for Block 004: OpenCode native capabilities, Serena for targeted symbol/navigation work,
and RTK for noisy shell commands.

## Active block

Block 004 - Beets Lifecycle Integration and Discogs Preview.

## Active spec

`docs/specs/004-beets-lifecycle-preview/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`

## Allowed files

The Noqlen plugin entry point, optional lifecycle helper, narrowly hardened Discogs error boundary,
focused deterministic/live tests, README, Block 004 specs, and context/handoff documents.

## Forbidden files

Domain/provider contract changes, candidate application, resolver/authority behavior, persistence,
MediaFile fields, OAuth, credential files, caching, other providers, beets core, unrelated files,
local tool configuration, and real user-library data.

## Non-goals

- Do not fork or patch beets core as part of the current project direction.
- Do not replace beets matching in the initial product scope.
- Do not apply preview candidates or alter beets matching/import choices.
- Do not use a real music library in automated tests.

## Behavior budget

One `import_task_choice` listener may invoke the production Discogs adapter only for a selected album
APPLY choice and print a safe normalized preview. It performs no metadata, database, or file writes.

## Validation

Baseline repository validation:

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
```

## Done when

Selected album APPLY tasks can produce a safe Discogs candidate preview, provider failures cannot
abort import, deterministic validation passes offline, and the opt-in direct-ID live smoke is
attempted before the scoped commit.

## Stop condition

Stop after Block 004. Do not implement candidate application, resolver/field authority, persistence,
metadata writes, or another provider.
