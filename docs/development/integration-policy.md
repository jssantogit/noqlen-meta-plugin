# Provider Integration Policy

## Purpose

Noqlen Meta uses a fast development path for external metadata services. The goal is to avoid duplicate implementation work while keeping tests deterministic and the production architecture trustworthy.

## Policy: real-first, fixture-backed

For a provider integration:

1. Implement the production adapter directly.
2. Keep network I/O behind a narrow, explicit boundary.
3. Validate representative behavior against the real service when appropriate and permitted.
4. Sanitize representative real responses before storing them as fixtures.
5. Test normal parsing, normalization, and domain behavior against fixtures without network access.
6. Keep live integration tests opt-in and outside the default test run.
7. Mock only failures that are impractical, wasteful, rate-limit-sensitive, destructive, or unsafe to reproduce against the live service.
8. Never use a real music library in automated tests.

## Fixture rules

Fixtures must not contain:

- credentials or authentication headers;
- personal paths or private user data;
- lyrics or fingerprints unless an explicitly approved test requires synthetic replacements;
- real local library paths;
- unnecessary full API payloads when a smaller representative payload is sufficient.

Prefer small fixtures that preserve the provider response shape needed by the parser.

## Live test rules

Live tests must:

- be explicitly marked `live`;
- be opt-in;
- avoid metadata or file writes;
- use documented public/catalog identifiers rather than user-library data;
- tolerate being skipped when credentials are unavailable;
- never be required for the normal local or CI test suite.

## Mocks

Use mocks primarily for boundary failures such as timeouts, HTTP errors, rate limits, malformed responses, and unavailable services. Do not create a second fake implementation of a provider when fixture-backed testing of the production adapter is sufficient.
