# Handoff

## State

Block 010 inserts an immutable, read-only `BeetsTargetPlan` after the canonical `ChangePlan`. The real
import flow analyzes whether planned changes fit current `AlbumInfo` fields losslessly and renders a
target-oriented preview while selected import state remains unchanged.

## Completed

- Exact beets targets and list/scalar shapes are declared in one immutable mapping table.
- Genres, country, year, and one-value style/label/catalog/barcode/media changes map losslessly.
- Multi-value to singular changes and unsupported fields become explicit mapping blockers.
- Malformed known-field shapes raise `BeetsMappingError` and are not treated as provider failures.
- Mapped changes and blockers retain the original `PlannedChange` and full candidate provenance.
- Target-plan categories and preview output are deterministic and resolver reviews remain visible.
- Real `AlbumInfo` compatibility is covered without mutating a music library.
- Existing providers, authority, confidence, failure isolation, one resolver pass, and read-only import
  snapshots remain unchanged.

## Important decisions

- `ChangePlan` remains canonical; `BeetsTargetPlan` describes only lossless target representation.
- A fully mapped plan is not writable, applicable, or approved.
- Multi-values are never silently collapsed or delimiter-serialized into singular beets fields.
- The target plan keeps genres as an immutable tuple; future list materialization is deferred.
- Candidate provenance is retained by structure and is not duplicated or persisted.
- No metadata, database, tags, files, plans, or provenance are written.

## Deferred

- Pre-apply safety checks, metadata application, partial-application policy, and provenance persistence.
- `beet noqlenmeta` and preferred `beet nm` alias.
- Confidence calibration, artwork, previews, lyrics, and additional provider adapters.

## Recommended next block

After independent Block 010 review, Block 011 may define the first explicit opt-in application boundary
for losslessly mapped changes. Plans with resolver reviews or mapping blockers require a separately
reviewed protection policy before any write path is allowed.
