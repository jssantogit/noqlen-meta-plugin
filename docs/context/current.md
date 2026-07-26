# Current Context

## Project

Noqlen Meta Plugin - universal multi-provider metadata enrichment for beets.

## Profile

`core-lib`

## Context level

`standard` for Block 007 because it integrates a second provider boundary with policy and the beets
import lifecycle.

## Tool Mode

`combo`: OpenCode native capabilities, Serena for targeted symbol/navigation work, and RTK for noisy
shell commands.

## Active block

Block 007 - iTunes Album Enrichment Provider and Real Multi-Provider Resolution.

## Active spec

`docs/specs/007-itunes-provider/`

## Active ADRs

- `docs/adr/0001-external-beets-plugin.md`
- `docs/adr/0002-python3-discogs-client.md`
- `docs/adr/0003-field-authority-resolution.md`

## Allowed files

The iTunes provider, plugin entry point, beets integration helpers, minimal resolver provider defaults,
focused tests and fixtures, README, Block 007 specs, and context/handoff documents.

## Forbidden files

Provider/domain contract redesign, candidate application, beets/file/database mutation, CLI,
semantic field merging, persistence, provider registry, caching, concurrency, Apple Music API,
artwork/previews, additional providers, advanced policy YAML, and beets core.

## Behavior budget

One concrete iTunes collection may emit genres/year candidates. Independently gated Discogs and iTunes
candidates share one Field Authority resolver pass with isolated failures. Safe decisions are
previewed and never applied.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Done when

iTunes direct/UPC/search paths are conservative, both real providers can coexist, authority outranks
confidence, failures are isolated, unnecessary calls are gated, and all selected beets state remains
unchanged.

## Stop condition

Stop after Block 007. Do not apply decisions or begin metadata writes, Last.fm, lyrics, artwork, or CLI.
