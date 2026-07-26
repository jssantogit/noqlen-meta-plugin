# Handoff

## State

Block 013 adds the first user-facing library command through one `noqlenmeta` Subcommand with `nm`
alias. It plans existing Albums through the same provider/resolver/ChangePlan path as importer
enrichment, then maps to a read-only `LibraryTargetPlan` and always previews without mutation.

## Completed

- `beet nm QUERY`, `beet noqlenmeta QUERY`, and explicit `beet nm --all` share one handler.
- A missing query fails before provider work; query plus `--all` is rejected.
- Native `Library.albums()` semantics select persistent Albums; no singleton mode exists.
- Album identity/current-value adapters trim and validate without fuzzy inference or Item queries.
- Importer and CLI invoke one shared provider collection, resolver, and ChangePlan helper.
- `LibraryTargetPlan` maps persistent Album fields losslessly and preserves provenance.
- Multi-value singular targets, media, format descriptions, and future unmapped fields are blockers.
- Resolver reviews and mapping blockers are safely rendered per album.
- CLI output and read-only behavior ignore importer `preview`, `apply`, and `apply_mode` settings.
- Provider failures remain isolated; internal contract and library mapping errors propagate.
- Tests guard Album/Item methods and snapshots to prove zero library or file mutation.

## Important decisions

- `noqlenmeta` is canonical and `nm` is an alias on the same Subcommand.
- CLI and importer diverge only after canonical ChangePlan construction.
- AlbumInfo application is not valid for persistent Album objects.
- Genres retain structured multi-values; singular persistent fields require exactly one value.
- Persistent Album has no album-level media target, and Item media behavior is deferred.
- Explicit CLI preview is unconditionally read-only regardless of importer application settings.

## Deferred

- CLI `--apply` and every database, Item, tag, and file-write semantic.
- Item inheritance and media mapping.
- Provenance persistence, confidence calibration, artwork, lyrics, and additional providers.

## Recommended next block

After independent Block 013 review, Block 014 may design `beet nm QUERY --apply` against the audited
`LibraryTargetPlan`. It must explicitly decide Album storage, Item inheritance, optional file tags,
media, strict/partial policy, and transaction boundaries; do not improvise those writes in Block 013.
