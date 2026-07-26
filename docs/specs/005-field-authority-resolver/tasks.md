# Tasks - Field Authority Resolver

## Block 005

- [x] Add immutable field rules and independent field/provider policy.
- [x] Add conservative default authority vocabulary and current Discogs operational defaults.
- [x] Add deterministic provider-independent resolution and explicit decisions.
- [x] Preserve structured values, selected provenance, and relevant alternatives.
- [x] Cover policy safety, authority, ambiguity, current values, immutability, and determinism.
- [x] Record the architecture in ADR 0003 and update project handoff.

## Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Stop condition

Stop before resolver lifecycle integration, metadata application, configuration migration, CLI,
semantic merging, persistence, or another provider.
