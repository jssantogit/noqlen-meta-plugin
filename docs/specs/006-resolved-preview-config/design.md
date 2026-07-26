# Design - Resolved Preview Configuration

## Data flow

```text
selected AlbumInfo -> ReleaseEnrichmentContext -> DiscogsProvider -> MetadataCandidate[]
selected AlbumInfo -> canonical current_values
plain field/provider settings -> default ResolutionPolicy overlay
current_values + candidates + policy -> resolve_metadata() -> FieldDecision[] -> safe preview
```

## Configuration boundary

The plugin owns Confuse access and converts known booleans into plain mappings. The integration helper
overlays only those known settings onto `default_resolution_policy()`, preserving authority,
confidence, and preserve-existing defaults. Unknown keys are not copied into policy.

## Provider gating

`ResolutionPolicy.provider_can_contribute(provider)` requires provider enablement and at least one
enabled field whose authority chain includes that provider. The plugin evaluates this before token
resolution and Discogs construction, avoiding all Discogs activity when it cannot affect a decision.

## Current values

The beets naming mismatch is isolated in `current_values_from_album_info()`. Genres retain ordered
non-empty entries. Style, label, catalog number, barcode, and media become single-entry tuples.
Country remains text and a valid positive year remains an integer. Format descriptions are absent
because there is no defensible selected-release source.

## Preview and failures

The renderer shows canonical field, action, current value, selected value/provider/confidence, and a
sanitized reason. Ambiguous review decisions show only a concise contender count and providers.
`ProviderError` remains a warning boundary; resolver errors propagate as programming defects.
