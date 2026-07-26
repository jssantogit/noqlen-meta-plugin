# ADR 0002: Use python3-discogs-client for Discogs access

- Status: Accepted
- Date: 2026-07-26

## Context

The Discogs provider needs maintained support for authentication, pagination, timeouts, rate limits,
backoff, and API errors. Building these concerns directly would add a second HTTP integration to
maintain without improving Noqlen's metadata behavior.

## Decision

Use `python3-discogs-client>=2.8,<3` as a Discogs-specific optional runtime dependency. Noqlen will
not build a hand-written Discogs HTTP client. The dependency remains behind `DiscogsProvider`, and
raw client objects, responses, and failures do not enter Noqlen's domain contracts.

Start with personal user-token authentication. It is sufficient for authenticated database search
and avoids OAuth callbacks, application consumer credentials, and token persistence before beets
configuration and lifecycle behavior are scoped.

## Consequences

- Direct release lookups can remain unauthenticated where Discogs permits them.
- Search callers must provide a personal token through the provider boundary.
- OAuth and credential storage remain deferred.
- Noqlen inherits the client's major-version compatibility and transitive HTTP stack, constrained by
  the `<3` upper bound.
