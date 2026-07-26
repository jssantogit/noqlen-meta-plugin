# Noqlen Meta Plugin

Universal metadata enrichment for beets.

Noqlen Meta is a beets plugin focused on enriching an already identified release with broader, field-aware metadata from multiple providers. The goal is not to replace beets' matcher. Beets remains responsible for release identification and import flow; Noqlen Meta adds a provider orchestration layer, field authority, conflict resolution, provenance, and reviewable enrichment.

## Project direction

The intended flow is:

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

Development uses a fast integration path for external providers:

1. Implement the production adapter directly.
2. Keep network I/O behind a narrow boundary.
3. Validate representative behavior against the real service when appropriate.
4. Store sanitized representative responses as fixtures.
5. Run normal automated tests against fixtures, without requiring network access.
6. Keep live integration tests opt-in.
7. Mock only failure conditions that are impractical or unsafe to reproduce against a real service.
8. Never use a real music library in automated tests.

## Current status

Repository bootstrap. No metadata provider or production enrichment behavior is implemented yet.

See `docs/context/current.md` for the active block and `docs/specs/001-project-foundation/` for the initial specification.
