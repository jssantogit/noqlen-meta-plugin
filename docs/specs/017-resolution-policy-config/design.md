# Design - Configurable Resolution Policy

## Flow

```text
default_resolution_policy()
  -> fields enablement overlay
  -> providers enablement overlay
  -> optional authority replacement
  -> optional confidence replacement
  -> optional preservation replacement
  -> ResolutionPolicy
```

Confuse extracts each nested section as a plain mapping. `resolution_policy_from_settings()` validates
advanced entries against baseline fields and current built-in providers, then uses `dataclasses.replace`
on existing `FieldRule` values. `ResolutionSettingsError` marks only invalid user overrides; the
plugin translates it and confuse extraction errors to the normal beets `UserError` boundary.

Provider invocation continues to require enablement, authority membership, and declared capability.
Confidence and preservation remain post-collection resolver concerns.
