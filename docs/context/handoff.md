# Handoff

## State

Block 005 adds a pure provider-independent resolver. Current metadata plus normalized candidates and a
`ResolutionPolicy` now produce immutable, explainable `FieldDecision` values. Nothing is applied to
beets, files, or the database.

## Completed

- `FieldRule` defines field enablement, normalized ordered authority, confidence eligibility, and
  preserve-existing behavior.
- `ResolutionPolicy` independently controls fields and providers with copied read-only mappings.
- Unknown fields/providers and unlisted authority providers are ineligible by default.
- Authority outranks confidence after threshold eligibility; eligible lower authority provides a
  fallback when higher authority is unavailable or below threshold.
- Same-provider conflicts review without an arbitrary winner; identical values deduplicate
  deterministically.
- Current values produce propose, keep, or review actions without mutation.
- Selected candidates retain their original structured value and source provenance; lower-authority
  contenders remain alternatives.
- The default policy enables current Discogs fields and only the implemented Discogs provider while
  recording disabled future authority vocabulary.

## Important decisions

- Field authority is not a global provider ranking.
- Field and provider enablement are independent.
- Existing metadata is preserved on conflict by default.
- Empty authority chains have safe skip semantics.
- Resolution creates decisions, never writes; semantic merging remains deferred.

## Deferred

- Resolver integration with selected `AlbumInfo` and the existing preview lifecycle.
- Mapping user-facing independent `fields` and `providers` configuration into policy.
- Metadata change plans/application, provenance persistence, and field-specific merge policy.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, lyrics, and additional provider adapters.

## Recommended next block

Block 006 should combine selected-release current values and provider candidates through the resolver,
then render a resolved preview/change plan. It should begin mapping independent field and provider
configuration without applying metadata. The manual CLI remains a later dedicated slice.
