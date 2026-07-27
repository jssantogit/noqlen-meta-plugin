# Review - Importer Track Planning Preview

## Review Focus

- Confirm only selected `AlbumMatch` mappings and singleton `TrackMatch` execute track planning.
- Confirm preview, provider, field, capability, and authority gates prevent ineligible LRCLIB calls.
- Confirm selected metadata uses album `merge_with_album` and singleton `item_data` exactly.
- Confirm `from_scratch` mirrors beets clear-then-overlay behavior: omitted `lyrics` clears and omitted
  flexible `synced_lyrics` survives.
- Confirm parity tests call actual album and singleton `apply_metadata()` for both fields, both modes,
  and selected-value presence/absence.
- Confirm `ProviderError` details cannot escape, later tracks continue, and contract errors propagate.
- Confirm release and track previews coexist without changing release application behavior.
- Confirm raw lyrics are never rendered and no track model, database, tag, or file mutation is
  reachable.
- Confirm the library CLI remains album-only and synchronized-lyrics target semantics remain open.

## Status

Implementation review and final offline validation are complete.

## Validation Evidence

- `.venv/bin/ruff check .`: passed.
- Focused track planning, preview, importer, track integration, and release integration suites: 161
  passed.
- `.venv/bin/pytest`: 723 passed, 5 opt-in live tests skipped.
- `.venv/bin/python scripts/check_repo_contamination.py`: passed.
- `git diff --check`: passed.

## Residual Risk

`synced_lyrics` is flexible metadata rather than a standard persistent Item media field in beets.
This preview models current behavior but intentionally does not choose a future application target.
