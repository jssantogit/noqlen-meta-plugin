# Handoff

## State

Block 006 integrates the Block 005 resolver into the selected-release import preview. User-facing
`fields` and `providers` configuration now controls Discogs eligibility independently, selected
`AlbumInfo` values are canonicalized, and resolved decisions are rendered without applying them.

## Completed

- Configuration uses `fields` for desired metadata and `providers.discogs` for the production source.
- Safe defaults keep preview enabled, Discogs disabled, current Discogs fields enabled, and future
  capabilities disabled.
- Plain settings are overlaid on `default_resolution_policy()` without exposing advanced policy YAML.
- `ResolutionPolicy.provider_can_contribute()` prevents provider calls unless an enabled provider has
  authority for at least one enabled field.
- Selected genres and singular style/label/catalog/barcode/media values use canonical tuple shapes;
  country and valid year remain scalar.
- The preview renders safe `KEEP`, `PROPOSE`, `REVIEW`, and `SKIP` decisions with selected provenance.
- Provider failures still warn and allow import to continue; resolver defects are not broadly caught.
- Integration tests snapshot `AlbumInfo`, choice, match, and items to enforce read-only behavior.

## Important decisions

- The old pre-release top-level `discogs` configuration is removed, not maintained in parallel.
- Unknown configured fields/providers are ignored and gain no authority.
- Provider-level gating avoids unnecessary API calls; Discogs responses are not field-filtered.
- Resolution creates preview decisions only and never writes.

## Deferred

- Metadata change plans/application, provenance persistence, and field-specific merge policy.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, lyrics, and additional provider adapters.

## Recommended next block

Review the real Block 006 branch before choosing between a safe metadata application/`ChangePlan`
slice and a second production provider. Do not assume that writes are next.
