# Handoff

## State

Version 1.0.0 was released successfully on 2026-08-02. Block 028 and the
atime-sensitive test hotfix are complete and merged. There is no active
development block; post-v1 update planning may now begin.

## Released

- Public package `beets-noqlenmeta==1.0.0` on PyPI.
- Existing annotated tag `v1.0.0` and matching GitHub Release.
- MIT License with copyright © 2026 João Pedro Rosa dos Santos.
- Python support bounded to 3.10-3.14 (`>=3.10,<3.15`).
- beets support bounded to `>=2.12,<3`.
- Tag-only, build-once PyPI publication through Trusted Publishing and OIDC.
- No API token or long-lived publishing credential.
- Public Read the Docs `latest`, `stable`, and `v1.0.0` builds.

## Product Surface

- Importer and existing-library ordinary metadata enrichment.
- Discogs, anchored MusicBrainz, Last.fm, iTunes, and LRCLIB adapters.
- Strict and partial ordinary database application policies.
- Separate MusicBrainz identity audit and repair for importer and library modes.
- Specialized four-MBID file-tag synchronization with fail-closed filesystem
  validation.
- Public English documentation, strict MkDocs build, release validation, and
  Python/beets compatibility CI.

## Release Validation

- Final `main` CI passed across Python 3.10-3.14, beets 2.12.0, the latest
  supported beets below 3, documentation, and package validation.
- The release workflow verified tag/version equality and remote-main ancestry,
  built wheel and sdist once, checked them, and published the same artifacts.
- PyPI metadata reports version 1.0.0 and semantic `Requires-Python
  >=3.10,<3.15`.
- Published wheel and sdist hashes match the workflow artifacts attached to the
  GitHub Release.
- The public-package clean-install plugin-discovery check and public
  `beet nm --help` check remain unchecked in `RELEASE_CHECKLIST.md` until run.

## Next Planning Target

The proposed first update is AcoustID/Chromaprint identity evidence. Planning
must compare the Forge Core implementation with the Meta Plugin architecture
instead of copying it blindly. Preserve beets as matcher/library manager and
keep provider lookup, identity evidence, database repair, and file writes behind
separate authority boundaries.

The planning pass should decide:

- whether existing beets fingerprints and AcoustID IDs are reused before local
  calculation;
- optional dependency and `fpcalc`/Chromaprint backend behavior;
- API-key handling, pacing, timeout, caching, and safe diagnostics;
- score and ambiguity rules;
- whether AcoustID writes only its own fields or may support MusicBrainz
  recording identity as evidence;
- importer versus existing-library scope;
- preview/apply boundaries and lossless target mappings;
- offline, fake-service, live opt-in, packaging, and documentation tests.

No implementation, package version bump, or new tag belongs in the post-release
state branch. Create an explicit spec and ADR before changing product behavior.
