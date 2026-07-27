# Requirements - Safe Partial Library Database Application

## Goal

Add explicit safe partial database application to the existing library command while retaining every
Block 014 guard.

## Requirements

- Keep preview as default and strict as the default `--apply` policy.
- Require `--apply --partial` to select partial CLI mode independently from importer configuration.
- Persist only mapped resolved fields; withhold reviews and mapping blockers visibly.
- Treat a partial plan with no mapped changes as a valid no-store outcome.
- Validate canonical plan integrity, local cleanliness, fresh persisted mapped state, all target
  values, and target uniqueness before any mutation.
- Persist the mapped subset once with `Album.store(inherit=True)` and normal Item inheritance.
- Keep plan-all-before-write, per-Album persistence, failure propagation, and no global rollback.
- Perform no physical tag, path, art, media-to-Item, or file operation.
