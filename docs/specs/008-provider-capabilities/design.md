# Design - Provider Capabilities and Orchestration

## Static metadata

`ProviderSpec` contains only canonical name, display name, and immutable supported fields. Built-in
specs live in a dependency-light module and are the source used by concrete adapters, orchestration,
resolver defaults, and preview branding.

## Contribution flow

```text
provider enabled
  + enabled field
  + provider in field authority
  + field in adapter capabilities
  -> invoke provider
```

`ResolutionPolicy.provider_has_enabled_authority()` answers only the policy portion. Orchestration
computes the capability-aware field intersection. Provider-specific token and storefront setup stays
explicit and Discogs remains lazily imported.

## Candidate contract

Successful responses are converted to tuples and checked against the selected spec. Provider name
mismatch or undeclared fields raise `ProviderContractError`; only `ProviderError` is converted to a
safe provider-specific warning. Valid candidates pass unchanged into the existing resolver.
