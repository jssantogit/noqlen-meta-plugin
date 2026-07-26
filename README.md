# Noqlen Meta Plugin

Universal metadata enrichment for beets.

Noqlen Meta is a beets plugin focused on enriching an already identified release with broader, field-aware metadata from multiple providers. The goal is not to replace beets' matcher. Beets remains responsible for release identification and import flow; Noqlen Meta adds a provider orchestration layer, field authority, conflict resolution, provenance, and reviewable enrichment.

## Project direction

```text
beets candidate matching
        ↓
selected release
        ↓
Noqlen Meta enrichment
        ↓
provider candidates
        ↓
field authority + resolver
        ↓
reviewable metadata changes
        ↓
beets database / file write
```

The first providers are expected to include MusicBrainz, Discogs, and AcoustID, followed by additional catalog, community, lyrics, and fallback sources where they add clear value.

## Development model

This repository follows the Noqlen Playbook workflow:

```text
Plan → Block → Prompt → Tool Mode → Implement → Validate → Audit → Fix → Commit → Handoff → Next block
```

For provider integrations, this project uses the repository's **real-first, fixture-backed** fast path. Production adapters are implemented directly, external I/O stays behind narrow boundaries, representative real responses may be sanitized into fixtures, normal tests remain offline and deterministic, live tests are opt-in, and failure-only mocks are used where reproducing failures against a real service would be wasteful or unsafe.

Automated tests must never use a real music library.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
ruff check .
python scripts/check_repo_contamination.py
```

Enable the plugin in a beets configuration after installing it into the same Python environment:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  discogs:
    enabled: false
    user_token: ""
  preview: true
```

Discogs enrichment is disabled by default. Set `discogs.enabled: true` to preview normalized Discogs
candidates after selecting an album match. A non-empty `NOQLENMETA_DISCOGS_TOKEN` takes precedence
over `user_token`; direct Discogs release-ID lookups do not require a token. Tokens are redacted and
never included in preview output.

The preview is read-only and normal beets metadata application continues unchanged:

```text
Noqlen Meta / Discogs:
  release: 123456
  genres: Electronic, Rock
  styles: Ambient
```

## Current status

The plugin can preview Discogs enrichment for a selected album release during import. Candidate
application, field authority, conflict resolution, and persistence are not implemented yet.

See `docs/context/current.md` and `docs/context/handoff.md` before starting a development block.
