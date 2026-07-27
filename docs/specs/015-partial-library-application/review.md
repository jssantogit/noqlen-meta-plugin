# Review - Safe Partial Library Database Application

## Scope Review

- [x] One Subcommand owns `noqlenmeta` and `nm` with `--apply` and `--partial`.
- [x] `--partial` requires `--apply`; importer settings remain unrelated.
- [x] Strict remains default and reviews/blockers still block all Album mutation.
- [x] Partial persists only mapped fields and reports every withheld class.
- [x] The mapped subset retains target integrity, dirty, fresh stale-state, materialization, and
  uniqueness guards.
- [x] Normal Album storage provides Item inheritance without physical file operations.
- [x] Plan-all-before-write and stop-after-failure behavior remain intact.

## Validation Evidence

- Focused library application and CLI tests: `55 passed`.
- `ruff check .`: passed.
- `pytest`: `395 passed`, with 2 live provider tests skipped by default.
- `python scripts/check_repo_contamination.py`: passed.
- `git diff --check`: passed.
- Isolated `beet help noqlenmeta` and `beet help nm`: passed and show `--apply` and `--partial`.

## Residual Risks

Multi-album application is not globally atomic. Earlier Album stores can remain committed after a
later failure. Database metadata and physical file tags intentionally diverge until a separately
authorized future synchronization boundary is designed.

## Final Status

Complete. Baseline validation and command discovery are green; commit and push remain.
