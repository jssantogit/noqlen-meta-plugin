# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 017 because it exposes existing resolver policy through shared importer and CLI
configuration without changing resolution, application, or persistence architecture.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 017 - Configurable Resolution Policy.

## Active spec

`docs/specs/017-resolution-policy-config/`

## Active ADRs

- `docs/adr/0003-field-authority-resolution.md`
- `docs/adr/0004-provider-capabilities-orchestration.md`
- `docs/adr/0012-anchored-musicbrainz-enrichment.md`
- `docs/adr/0013-configurable-resolution-policy.md`

## Allowed files

Shared policy integration, plugin configuration extraction, focused pure/importer/CLI tests, README,
ADR 0013, Block 017 specs, and context/handoff documents.

## Forbidden files

Resolver redesign, provider modules, mappings, application or persistence semantics, new fields or
providers, CLI flags, caching/concurrency, beets core, and physical file operations.

## Behavior budget

Optional field-level authority, confidence, and preservation overrides may alter resolution decisions
and existing capability-gated provider invocation. Missing overrides preserve built-in policy exactly.
No override grants write permission.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

The three optional mappings validate strictly, overlay built-in `FieldRule` values, affect importer
and CLI through one policy, preserve capability independence and write safety, and all offline
validation passes.

## Stop condition

Stop after Block 017. Do not add Last.fm or physical tag synchronization.
