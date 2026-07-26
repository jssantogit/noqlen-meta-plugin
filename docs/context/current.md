# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 006 because it integrates policy, provider I/O, and the beets import lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 006 - Resolved Import Preview and Fields/Providers Configuration.

## Active spec

`docs/specs/006-resolved-preview-config/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`

## Allowed files

The plugin entry point, beets integration helpers, a minimal resolver query, focused tests, README,
Block 006 specs, and context/handoff documents.

## Forbidden files

Provider/domain contract redesign, candidate application, beets/file/database mutation, CLI,
semantic field merging, persistence, another provider, advanced policy YAML, and beets core.

## Behavior budget

Selected `AlbumInfo` is copied to canonical current values, Discogs candidates are resolved through
configured field/provider policy, and safe decisions are previewed. No decision is applied.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

The actual import preview uses the resolver, configuration independently gates fields and providers,
unusable providers are not called, and all selected beets state remains unchanged.

## Stop condition

Stop after Block 006. Do not apply decisions or begin Block 007.
