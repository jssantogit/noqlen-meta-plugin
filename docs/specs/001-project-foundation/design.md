# Design — Project Foundation

## Design summary

Use the standard external beets plugin namespace and keep the initial package intentionally small. Establish workflow/safety boundaries before product implementation, but do not pre-build provider abstractions or fake frameworks.

## Boundaries

```text
beets
  └── loads beetsplug.noqlenmeta
          └── NoqlenMetaPlugin

future product layers
  provider I/O → normalization → candidate/domain model → authority/resolver → beets integration
```

Only the plugin entry class exists in this foundation block. Future layers require their own scoped specs/blocks.

## Packaging

- Distribution name: `beets-noqlenmeta`.
- Plugin name in beets configuration: `noqlenmeta`.
- Python package namespace: `beetsplug.noqlenmeta`.
- Python compatibility starts at 3.10 to align with the current beets 2.x support floor.

## Validation design

Default validation is offline:

- Ruff for static lint checks.
- Pytest for focused behavior tests.
- Repository contamination script for prohibited local/tooling artifacts and obvious secret/path leakage.

Live provider checks will be opt-in in future blocks.

## Security considerations

No secrets, credentials, personal paths, real library metadata, lyrics, or fingerprints belong in source fixtures. Provider credentials must eventually enter through environment/config boundaries without being logged or committed.

## Alternatives considered

- Full fake-first provider framework: rejected as the default because it duplicates production work and increases Codex cost.
- No testing boundary at all: rejected because deterministic validation is required for confidence.
