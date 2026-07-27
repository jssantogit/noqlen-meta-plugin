# Review - Configurable Resolution Policy

## Scope Review

- [x] Built-in defaults remain authoritative when advanced settings are absent.
- [x] Authority, confidence, and preservation independently replace one field-rule property.
- [x] Configured authority validates current built-ins without validating capabilities.
- [x] Existing capability gating consumes configured authority.
- [x] Invalid settings fail before provider and library work.
- [x] Importer and CLI share policy construction and retain existing write permissions.
- [x] Resolver, provider, mapping, application, persistence, and file behavior are unchanged.

## Validation Evidence

- `ruff check .`: passed.
- `pytest`: `476 passed`, with 3 live provider tests skipped by default.
- `python scripts/check_repo_contamination.py`: passed.
- `git diff --check`: passed.
- Missing advanced settings were manually confirmed equal to `default_resolution_policy()`.

## Residual Risks

Nested mapping extraction depends on the supported confuse API provided through beets. Unknown
resolution sections are detected through its mapping-key interface.

## Final Status

Implementation and baseline validation complete; commit and push remain.
