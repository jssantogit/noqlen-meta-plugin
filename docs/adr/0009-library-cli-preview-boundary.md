# ADR 0009: Establish a read-only library CLI preview boundary

- Status: Accepted
- Date: 2026-07-26

## Context

Importer enrichment targets selected `AlbumInfo`, while a command over an existing library targets
persistent `library.Album` and potentially its Items. These models are not interchangeable:
persistent Album has the relevant catalog fields but has no album-level `media` field. A library
command therefore needs an audited target map before any write semantics can be designed.

## Decision

- `noqlenmeta` is the canonical beets command and `nm` is its alias through one `Subcommand`.
- The first library command is preview-only and operates on existing library Albums.
- A native beets album query is required unless `--all` is explicit; query plus `--all` is rejected.
- CLI and importer share provider collection, candidate validation, Field Authority resolution, and
  `ChangePlan` construction. They diverge only after `ChangePlan` because their targets differ.
- Persistent Album mapping is explicit, immutable, and read-only. AlbumInfo application code is not
  reused against library Album objects.
- `genres` maps as structured multi-value data. Singular Album fields accept exactly one canonical
  tuple value; multiple values are blockers and are never reduced or serialized.
- Persistent Album has no supported album-level `media` target in this block. `media` and
  `format_descriptions` are blockers, and Items are not queried to infer or apply media.
- Unknown valid canonical fields become mapping blockers. Malformed known canonical shapes raise a
  library mapping contract error.
- The command uses field/provider configuration and provider settings, but importer `preview`,
  `apply`, and `apply_mode` grant no CLI write permission and do not suppress explicit CLI preview.
- No database, Album, Item, tag, file, art, move, copy, or importer-application write occurs.
- CLI application is deferred to a separate reviewed block that must decide persistence, Item
  inheritance, file tags, media, policy, and transaction boundaries.

## Consequences

Users can safely inspect enrichment for one or more library albums without accidental mass provider
work or mutation. The explicit `LibraryTargetPlan` makes persistent-model limitations visible and
provides an audited planning boundary for a future application design without implying permission to
write.
