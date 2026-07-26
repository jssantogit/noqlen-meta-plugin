# Design - Field Authority Resolver

## Flow

```text
current Mapping[str, MetadataValue]
        + MetadataCandidate sequence
        + ResolutionPolicy
        -> group by canonical field
        -> filter by field/provider/authority/confidence policy
        -> choose by per-field authority
        -> compare with current value
        -> immutable FieldDecision tuple
```

## Policy

`FieldRule` normalizes and rejects duplicate provider authority names and validates a finite inclusive
confidence threshold. An empty authority chain means no provider is automatically eligible.
`ResolutionPolicy` copies its input maps into read-only mappings and treats unknown fields and
providers conservatively.

The default table enables the nine fields currently emitted by Discogs and enables only Discogs as a
provider. Planned fields and providers appear only as disabled authority vocabulary.

## Resolution

Eligible candidates meet all field, provider, authority-list, and confidence requirements. The first
eligible authority rank wins regardless of a fallback's higher confidence. Identical values from one
provider collapse deterministically; conflicting values at the winning provider require review.
Lower-authority contenders remain attached as alternatives.

The selected value is proposed when current metadata is absent, kept when exactly equal, reviewed on
conflict by default, and proposed on conflict only when preserve-existing is disabled. No decision is
a write.
