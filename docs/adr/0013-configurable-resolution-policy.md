# ADR 0013: Configure field-level resolution policy

- Status: Accepted
- Date: 2026-07-27

## Context

Noqlen already resolves normalized candidates with immutable per-field `FieldRule` values. Users can
choose wanted fields and enable providers, but cannot yet override the existing authority,
confidence, or existing-value preservation controls.

## Decision

1. Built-in resolution defaults remain the source of truth.
2. Advanced `resolution` configuration is optional, and missing or empty overrides preserve current
   behavior exactly.
3. `fields` controls whether a field is wanted; `providers` controls provider enablement.
4. `resolution.authority` controls ordered provider preference per field. An override replaces,
   rather than merges with, that field's default authority list.
5. Empty authority overrides are invalid; field disablement uses `fields`.
6. Configured authority providers must be current built-ins: Discogs, MusicBrainz, or iTunes.
7. Authority remains independent from Provider Capabilities. Capability gating still avoids adapters
   that cannot contribute a configured field.
8. `resolution.min_confidence` is field-level, finite, and within `0.0..1.0`.
9. `resolution.preserve_existing` is field-level. `false` permits a conflicting current value to
   become `PROPOSE` instead of `REVIEW`.
10. Resolution configuration never grants write permission.
11. Invalid explicit overrides fail before provider work.
12. Importer and CLI construct the same configured `ResolutionPolicy`.
13. The resolver implementation and ranking algorithm remain unchanged.
14. Mapping, application, persistence, and file behavior remain unchanged.

## Consequences

Users can refine provider preference and safety by field without creating another resolution engine.
Confidence cannot outrank authority, cannot pre-gate provider calls, and is not provider-specific.
Existing importer `apply: true` and CLI `--apply` boundaries remain the only write permissions.
