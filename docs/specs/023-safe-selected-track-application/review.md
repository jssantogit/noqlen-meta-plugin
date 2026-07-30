# Review - Safe Selected-Track Application

## Review Focus

- Confirm only selected `TrackInfo.lyrics` can mutate and Item/AlbumInfo stay unchanged.
- Confirm strict blocks reviews/blockers and partial applies only the mapped subset.
- Confirm integrity, effective-current stale, shape, value, and uniqueness checks precede mutation.
- Confirm track caches are invalidated and real later beets match application receives new lyrics.
- Confirm Noqlen never invokes match application, persistence, or file-write APIs.
- Confirm preview-disabled application, singleton parsing, per-track isolation, and sanitized output.
- Confirm synchronized lyrics and the library CLI remain unchanged.

## Status

Implementation and final offline validation are complete.

## Validation Evidence

- Focused application/mapping/planning/preview/importer/release/library suite: 176 passed.
- Full suite: 798 passed, 5 opt-in live tests skipped.
- Ruff, repository contamination, and diff-whitespace checks passed.

## Residual Risk

Native synchronized/SYLT representation remains intentionally unsupported. Downstream persistence
and file behavior is owned by normal beets and was not exercised against a real library.
