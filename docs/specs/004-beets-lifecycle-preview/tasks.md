# Tasks - Beets Lifecycle Preview

## Block 004

- [x] Correct active context from Block 003 to Block 004.
- [x] Narrow expected Discogs provider failures and test programming-error propagation.
- [x] Add disabled-by-default Discogs configuration, token redaction, and environment precedence.
- [x] Map selected `AlbumInfo` into a provider-independent release context.
- [x] Register and constrain the `import_task_choice` listener.
- [x] Invoke the production provider with graceful failure behavior.
- [x] Render a compact read-only candidate preview.
- [x] Add deterministic lifecycle tests and an opt-in direct-ID live smoke test.
- [x] Document configuration, design, and next-block handoff.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
NOQLEN_LIVE_TESTS=1 pytest -m live
```

## Stop condition

Stop before candidate application, resolver/field authority, provenance persistence, metadata
writes, OAuth, track enrichment, another provider, or beets core changes.
