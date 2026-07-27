# Handoff

## State

Block 017 exposes existing field-level resolution controls as optional configuration. Built-in
`default_resolution_policy()` remains the source of truth, and importer and CLI share one overlay.

## Completed

- Added empty-by-default authority, confidence, and preservation mappings.
- Added strict field, provider, authority-sequence, confidence, and boolean validation.
- Added user-facing configuration errors before provider and library work.
- Preserved authority/capability separation while making configured authority affect invocation.
- Proved authority and confidence selection with the real resolver.
- Proved preservation changes `REVIEW` to `PROPOSE` without granting importer or CLI writes.
- Documented optional configuration, replacement semantics, capability independence, and safety.

## Important decisions

- Authority overrides replace one field's complete order; omitted fields retain complete defaults.
- Only current built-in providers are valid in user authority overrides.
- Capability support is not configuration validation.
- Confidence remains field-level and post-collection.
- Resolution configuration never changes mapping, application, persistence, or file behavior.

## Deferred

- Last.fm community classification and any additional providers.
- Dynamic provider registration or capability overrides.
- Physical file-tag synchronization.

## Recommended next block

Stop for independent Block 017 audit. After audit, reassess Last.fm classification for genres,
styles, and mood as a separate block.
