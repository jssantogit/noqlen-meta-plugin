# Requirements - Beets Lifecycle Preview

## Goal

Invoke Discogs enrichment after a user selects an album match and show normalized candidates without
changing normal beets import behavior.

## Functional requirements

- Configure Discogs disabled by default, preview enabled by default, and redact the configured token.
- Prefer a non-empty `NOQLENMETA_DISCOGS_TOKEN` over the configured personal token.
- Listen at `import_task_choice` and run only for selected album `APPLY` tasks.
- Map selected `AlbumInfo` identity into `ReleaseEnrichmentContext` without mutation.
- Invoke the production `DiscogsProvider`; warn safely on `ProviderError` and continue import.
- Print compact normalized candidate fields and Discogs release identity when preview is enabled.
- Narrow provider I/O handling to expected external failures while allowing programming errors to
  propagate.
- Keep default tests offline and provide an environment-gated direct-release live smoke test.

## Non-goals

Candidate application, resolver/field authority, provenance persistence, MediaFile fields, database
or file writes, OAuth, candidate search integration, track enrichment, and beets core changes.

## Acceptance criteria

Focused tests prove configuration, mapping, lifecycle exclusions, graceful failures, safe preview,
and read-only behavior. Baseline validation passes and the separate live smoke is attempted.
