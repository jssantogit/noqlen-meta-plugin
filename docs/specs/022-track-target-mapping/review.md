# Review - Track Target Mapping

## Review Focus

- Confirm `lyrics` maps only and exactly to `TrackInfo.lyrics`.
- Confirm `synced_lyrics` never maps to `lyrics` or an arbitrary flexible target.
- Confirm both LRCLIB forms remain distinct when proposed together.
- Confirm resolver `REVIEW` is not reported as a mapping blocker.
- Confirm unknown fields block and target mapping is deterministic and immutable.
- Confirm preview exposes no lyric content or timestamps.
- Confirm no TrackInfo, Item, database, tag, or file mutation was added.
- Confirm release application and the album-only library CLI are unchanged.

## Status

Implementation review and final offline validation are complete.

## Validation Evidence

- Focused mapping/planning/preview/importer suite: 85 passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/pytest`: 766 passed, 5 opt-in live tests skipped.
- `.venv/bin/python scripts/check_repo_contamination.py`: passed.
- `git diff --check`: passed.

## Residual Risk

Native synchronized/SYLT representation is intentionally unsupported. A later application block
must add integrity and stale-state guards before mutating even the losslessly mapped plain-lyrics
target.
