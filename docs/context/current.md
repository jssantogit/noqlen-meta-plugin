# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 005 because it establishes resolver architecture and an ADR.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 005 - Field Authority and Resolver Core.

## Active spec

`docs/specs/005-field-authority-resolver/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`

## Allowed files

Provider-independent resolver/policy code, focused synthetic tests, ADR 0003, Block 005 specs, and
context/handoff documents.

## Forbidden files

Lifecycle/provider changes, candidate application, beets/file/database mutation, configuration
migration, CLI, semantic field merging, persistence, another provider, and beets core.

## Behavior budget

Pure resolution from current values, normalized candidates, and immutable policy into immutable field
decisions. No decision is applied.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

Field/provider policy and deterministic authority resolution are tested, documented, and validated;
current conflicts review by default and provenance remains structured.

## Stop condition

Stop after Block 005. Do not integrate the resolver into beets or begin Block 006.
