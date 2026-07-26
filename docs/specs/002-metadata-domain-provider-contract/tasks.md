# Tasks - Metadata Domain and Provider Contract

## Block 002

- [x] Confirm album-level hints available from the current beets release interface.
- [x] Add immutable release context and generic external identifier.
- [x] Add validated scalar and multi-value metadata candidate.
- [x] Add synchronous provider protocol and minimal provider error.
- [x] Add focused synthetic tests.
- [x] Update context and handoff.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Stop condition

Stop before implementing a concrete provider, resolver, authority policy, persistence, custom media
fields, or a beets lifecycle hook.
