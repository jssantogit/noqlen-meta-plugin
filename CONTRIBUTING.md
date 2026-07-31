# Contributing

## Development Setup

Use Python 3.10 or later and install the project in an isolated environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Tests

Normal development and CI are offline:

```bash
pytest -m "not live"
ruff check .
python scripts/check_repo_contamination.py
```

Live provider tests are opt-in and never required for a pull request. Run them
only when network access and any required credentials are intentionally
configured:

```bash
pytest -m live
```

Never use a real music library or copyrighted media in automated tests. Use
temporary beets databases, synthetic metadata, sanitized provider fixtures,
and the generated-silence media fixtures.

## Documentation

Install the pinned documentation environment and build strictly:

```bash
python -m pip install -r requirements-docs.txt
python scripts/check_public_docs.py
mkdocs build --strict
```

Remove generated `site/` output before committing.

## Pull Requests

Keep changes focused and explain the user-visible behavior. Add regression
tests, update the canonical public reference when flags or configuration keys
change, and report focused plus full validation. Do not commit credentials,
private paths, local tool configuration, generated package/site output, or
real-library data.

Before requesting review, run the focused tests for the change, the full
offline suite, Ruff, documentation checks when relevant, repository hygiene,
and `git diff --check`.
