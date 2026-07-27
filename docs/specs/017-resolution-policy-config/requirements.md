# Requirements - Configurable Resolution Policy

- Add optional `resolution.authority`, `resolution.min_confidence`, and
  `resolution.preserve_existing` mappings.
- Preserve the complete built-in policy when settings or individual fields are omitted.
- Replace authority per field; reject empty, duplicate, scalar, unknown-provider, and unknown-field
  overrides.
- Accept only finite numeric confidence in `0.0..1.0` and actual booleans for preservation.
- Keep authority independent from capabilities and use it in existing provider invocation gating.
- Fail invalid configuration before provider, library query, mutation, or database work.
- Share one configured policy across importer and CLI without changing resolver or application logic.
