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
  preview: true

  fields:
    genres: true
    styles: true
    labels: true
    catalog_numbers: true
    barcodes: true
    country: true
    year: true
    media: true
    format_descriptions: true
    mood: false
    lyrics: false
    synced_lyrics: false
    cover: false

  providers:
    discogs:
      enabled: false
      user_token: ""
```

`fields` controls what Noqlen may enrich. `providers` controls where Noqlen may obtain metadata.
Discogs enrichment is disabled by default. Set `providers.discogs.enabled: true` to preview resolved
Discogs decisions after selecting an album match. A non-empty `NOQLENMETA_DISCOGS_TOKEN` takes
precedence over `providers.discogs.user_token`; direct Discogs release-ID lookups do not require a
token. Tokens are redacted and never included in preview output.

The pre-release `noqlenmeta.discogs` configuration from Block 004 has been replaced rather than
retained as a parallel schema. Move its values under `noqlenmeta.providers.discogs`.

The preview is read-only and normal beets metadata application continues unchanged:

```text
Noqlen Meta / resolved preview:

  genres
    PROPOSE
    candidate: Electronic, Rock
    source: Discogs
    confidence: 0.92
    reason: selected 'discogs' by field authority; current value is missing
```

## Current status

The plugin resolves Discogs candidates against selected-release metadata and previews
`KEEP`/`PROPOSE`/`REVIEW`/`SKIP` decisions during import. The flow remains read-only; candidate
application and persistence are not implemented.

See `docs/context/current.md` and `docs/context/handoff.md` before starting a development block.
