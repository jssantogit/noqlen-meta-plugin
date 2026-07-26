# Requirements - Resolved Preview Configuration

## Goal

Integrate the field-authority resolver into the selected album import preview while introducing
independent user-facing `fields` and `providers` controls. The complete block remains read-only.

## Functional requirements

- Configure preview, known fields, and `providers.discogs` with safe defaults.
- Resolve the Discogs token from a non-empty environment value before the configured redacted value.
- Overlay field/provider booleans onto `default_resolution_policy()` without exposing advanced policy.
- Treat unknown configuration keys conservatively and grant no implicit authority.
- Skip Discogs I/O when disabled or unable to contribute to any enabled authoritative field.
- Convert selected `AlbumInfo` metadata to canonical resolver fields and compatible value shapes.
- Resolve provider candidates into `FieldDecision` values and render safe decision-oriented output.
- Keep provider service failures separate from resolver programming failures.

## Safety requirements

- Do not mutate import task state, `AlbumInfo`, items, albums, files, tags, or database records.
- Do not apply `PROPOSE` decisions or auto-accept `REVIEW` decisions.
- Do not expose tokens, raw responses, control characters, or complete contender structures.
- Keep normal tests offline and preserve the existing opt-in Discogs live smoke.

## Out of scope

Metadata writes, provenance persistence, CLI commands, additional providers, advanced policy YAML,
semantic merging, caching, concurrency, lyrics, artwork, and identification changes.
