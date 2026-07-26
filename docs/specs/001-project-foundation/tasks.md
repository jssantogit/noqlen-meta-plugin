# Tasks — Project Foundation

## Block 001: Repository bootstrap

### Goal

Prepare the repository for scoped Noqlen Meta development without implementing product behavior.

### Allowed files

- Root project metadata/documentation.
- `beetsplug/noqlenmeta/__init__.py`.
- Foundation tests.
- `docs/context/**`.
- `docs/development/**`.
- `docs/adr/**`.
- `docs/specs/001-project-foundation/**`.
- `scripts/check_repo_contamination.py`.
- `.github/workflows/ci.yml`.

### Forbidden files

- Provider implementations.
- Resolver/authority implementations.
- Real music-library fixtures.
- Credentials or local agent configuration.
- Release/publishing automation.

### Validation

```bash
ruff check .
pytest
python scripts/check_repo_contamination.py
```

### Done when

The package scaffold, workflow context, architecture record, integration policy, tests, and CI baseline are present and no product enrichment behavior has been introduced.

### Stop condition

Stop if bootstrap requires implementing provider behavior, modifying beets core, using real user-library data, or publishing a release.
