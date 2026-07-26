# Tasks - Discogs Album Enrichment Provider

## Block 003

- [x] Add the optional `python3-discogs-client` dependency and ADR 0002.
- [x] Implement direct release-ID lookup and bounded authenticated search.
- [x] Implement conservative deterministic edition selection.
- [x] Fetch a concrete release and normalize album metadata candidates.
- [x] Add sanitized release/search fixtures and offline production-path tests.
- [x] Translate external failures to `ProviderError`.
- [x] Update context and handoff documents.

## Validation

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python scripts/check_repo_contamination.py
git diff --check
git status --short
```

## Stop condition

Stop before beets lifecycle/configuration, resolver/authority behavior, OAuth, Master Release lookup,
caching, persistence, writes, track enrichment, or another provider.
