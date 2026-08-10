# Provider Integration Policy

## Purpose

Noqlen Meta uses a fast, evidence-driven path for external metadata services.
The goal is to avoid duplicate implementation work while keeping production
boundaries trustworthy and normal tests deterministic and offline.

## Policy: real-first, fixture-backed

For a provider integration:

1. Implement the production adapter directly.
2. Keep network or process I/O behind a narrow, explicit boundary.
3. When cheap, safe, and useful, observe the real provider outcome with a
   documented public/catalog identifier instead of relying only on agent or
   implementation claims.
4. Preserve a sanitized representative response as a fixture only when it adds
   durable regression value; do not collect fixtures by ritual.
5. Test parsing, normalization, mapping, and domain behavior offline against
   the smallest useful fixtures or synthetic inputs.
6. Keep live integration tests opt-in and outside the default test run.
7. Mock boundary failures that are impractical, wasteful, rate-limit-sensitive,
   destructive, private-state-dependent, or unsafe to reproduce live.
8. Do not create a second provider implementation, interface, or abstraction
   merely so a fake can exist.
9. Never use a real user music library in automated tests.

## Outcome verification

Direct observation complements automated tests when it cheaply catches an
integration failure that internal tests may miss. Useful examples include:

- one bounded provider lookup using a stable public identifier;
- one safe CLI preview over synthetic or public test input;
- inspection of a sanitized parsed result;
- documentation or configuration rendering when the integration changes its
  public surface.

A live call is not a universal gate. Skip it when credentials, rate limits,
privacy, nondeterminism, service availability, or cost make deterministic
fixtures stronger evidence for the task.

## Fixture rules

Fixtures must not contain:

- credentials or authentication headers;
- personal paths or private user data;
- lyrics or fingerprints unless an explicitly approved test uses synthetic
  replacements;
- real local library paths;
- unnecessary full API payloads when a smaller representative payload is
  sufficient.

Prefer small fixtures that preserve only the provider response shape needed by
the behavior under test.

## Live test rules

Live tests must:

- be explicitly marked `live`;
- be opt-in;
- avoid metadata or file writes;
- use documented public/catalog identifiers rather than user-library data;
- tolerate being skipped when credentials are unavailable;
- never be required for the normal local or CI test suite.

## Mocks and isolation

Use the lightest isolation technique that proves the behavior. A fixture,
simple stub, injected boundary failure, or temporary state is often sufficient.

Mocks are most useful for conditions such as timeouts, HTTP errors, rate
limits, malformed responses, unavailable services, and other failures that are
not useful to reproduce against a real provider.

Do not promote a testing convenience into a new production abstraction unless
the product itself benefits from that boundary.
