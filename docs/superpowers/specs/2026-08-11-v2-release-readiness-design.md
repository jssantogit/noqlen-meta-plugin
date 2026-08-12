# Noqlen Meta v2 Release Readiness Design

## Status

Approved product direction: release-readiness only. The v2 functional code is frozen for this pass.

Integration base: `docs/v2-enrichment-design` at `5db79cb64c35cb81f927316ef514c6020947fa80`.

Working branch: `chore/v2-release-readiness`.

Target release version: `2.0.0`.

## Goal

Turn the fully integrated v2 implementation into a coherent release candidate without adding, removing, or redesigning product behavior.

The pass aligns package metadata, public release documentation, changelog, release checks, and stale architectural wording with the already-approved v2 behavior. It must leave the repository in a state where the only remaining product decision is whether to merge the release candidate into `main`. Tagging and publication remain separate owner-authorized actions.

## Non-Goals

This pass must not:

- add new enrichment fields, providers, analyzers, commands, flags, or configuration options;
- refactor working enrichment, identity, AcoustID, artwork, BPM, file-sync, or importer behavior merely for cleanliness;
- change default provider or field behavior;
- change the approved Artwork + Audio semantics;
- add an external BPM provider;
- add local ML mood analysis;
- merge into `main`;
- create a `v2.0.0` tag;
- create a GitHub Release;
- publish to PyPI;
- change the release workflow's trusted-publishing security model.

## Release Candidate Version

`pyproject.toml` changes from `1.0.0` to `2.0.0` on the release-readiness branch.

This is release-candidate preparation, not publication. The version bump does not authorize a tag or release by itself.

The existing `.github/workflows/release.yml` contract remains authoritative:

- publishing is triggered only by a `v*` tag;
- the tag must match `pyproject.toml` exactly;
- the tagged commit must be contained in remote `main`;
- distributions are built once and published through PyPI Trusted Publishing/OIDC;
- no long-lived publishing credential is introduced.

## Changelog

`CHANGELOG.md` becomes a user-facing v2 release record rather than leaving the completed work as a narrow AcoustID-only `Unreleased` section.

Add a dated release section:

```text
## 2.0.0 - 2026-08-11
```

The section summarizes user-visible changes, not implementation history. It must cover at least:

### Added

- generalized release, track, and artist semantic enrichment;
- multivalued styles and moods;
- lyrics-language, artist-language, artist-country, and artist-area enrichment;
- genre taxonomy/promotion behavior introduced by the v2 genre foundation;
- verified ordinary metadata file synchronization behind `--apply --write`;
- album artwork owned by Noqlen Meta through Cover Art Archive, `cover.jpg`, `Album.artpath`, multidisc handling, and optional embedding;
- opt-in local BPM analysis through the `[audio]` extra and lazy Librosa backend;
- existing-library AcoustID evidence workflow completed since v1.

### Changed

- `--write` is now the general audio-file mutation authority for ordinary enrichment when combined with `--apply`;
- `--apply` remains the ordinary database authority but may also create/replace authorized `cover.jpg` sidecars and persist `Album.artpath`; therefore public wording must no longer describe all `--apply` behavior as strictly database-only;
- v2 canonical styles/moods and related semantic fields are losslessly multivalued;
- local BPM analysis is opt-in by default and preserves existing BPM unless explicit recalculation is configured.

### Safety

Summarize the major preserved guarantees:

- preview remains non-mutating;
- `--write` never triggers additional provider lookup or analysis;
- artwork selection and binary application are separated;
- file writes use verified planning/application boundaries;
- identity and AcoustID remain isolated from ordinary enrichment semantics;
- no force mode is introduced.

Keep a new empty `## Unreleased` section above `2.0.0` for future work.

## Public Documentation Alignment

Update only pages that describe release/version state or contradict the final v2 permission model.

### Release/status pages

Update:

- `site-docs/project/release.md`
- `site-docs/project/changelog.md`
- public landing/status wording where it materially presents v1 as the current package behavior.

The documentation may state that `1.0.0` is the currently published public release until `2.0.0` is actually published. It must distinguish:

- repository release candidate: `2.0.0`;
- currently published PyPI/GitHub release: `1.0.0` until release execution occurs.

Do not falsely claim that `v2.0.0`, a 2.0.0 PyPI distribution, versioned 2.0.0 Read the Docs build, or GitHub Release already exists.

### Permission wording

Remove stale blanket assertions that ordinary `--apply` is "database-only".

The final public contract is:

- preview: no mutation;
- ordinary `--apply`: ordinary database changes plus authorized artwork sidecars/`Album.artpath`; no audio-file mutation;
- ordinary `--apply --write`: same prepared work plus supported metadata/BPM tag synchronization and prepared artwork embedding;
- adding `--write` does not expand network/provider/analyzer work;
- identity, AcoustID, and identity-tag modes keep their existing separate authorities.

`site-docs/reference/commands.md` is already the strongest source for this matrix and should be used as the consistency reference.

## Public Documentation Validator

Update `scripts/check_public_docs.py` so it validates the v2 release candidate instead of enforcing v1-only wording.

Required changes:

- retain checks that current public 1.0.0 publication links/state are truthful until 2.0.0 is actually released;
- stop requiring a blanket ordinary `--apply` database-only statement;
- require the v2 distinction that `--apply` may write verified `cover.jpg` sidecars but does not mutate audio files without `--write`;
- require `--write` to be documented as not expanding provider/analysis work;
- require the v2 changelog section and version metadata to agree;
- preserve secret/private-path/internal-doc guards.

Do not weaken validation merely to make docs pass; update the asserted public contract to match production behavior.

## Release Checklist

Preserve the completed v1 history. Add a dedicated v2 release-candidate section instead of rewriting completed v1 checkmarks as if they applied to v2.

The v2 section should track at least:

### Release candidate preparation

- package version is `2.0.0`;
- changelog contains `2.0.0 - 2026-08-11`;
- public docs distinguish current published 1.0.0 from prepared 2.0.0;
- full offline suite and Ruff pass;
- Python 3.10-3.14 matrix passes;
- beets 2.12.0 and latest `<3` compatibility pass;
- `[audio]` Librosa lane passes;
- strict MkDocs/public-doc validation passes;
- package build/Twine/distribution inspection/clean-install smoke pass;
- diff contains no unintended functional feature work.

### Owner-authorized release execution

Leave these unchecked in the release candidate:

- merge release candidate into `main`;
- confirm final `main` CI;
- create `v2.0.0` tag on a commit contained in `main`;
- let tag workflow build and publish through trusted publishing;
- create/verify GitHub Release;
- verify PyPI `2.0.0` artifacts;
- verify Read the Docs versioned/stable state after publication.

Release-readiness must not mark any future external action complete before it happens.

## Release Contract Tests

Update `tests/release/test_release_contracts.py` and documentation tests as needed so automated assertions describe both:

1. historical v1 publication facts that remain true; and
2. the prepared v2 release-candidate state.

At minimum, tests must prove:

- project version is exactly `2.0.0`;
- Python support remains `>=3.10,<3.15` and classifiers/matrix remain 3.10-3.14;
- release workflow still requires a matching tag contained in `main` before publication;
- Trusted Publishing/OIDC contract is unchanged;
- `CHANGELOG.md` includes an `Unreleased` section above `2.0.0`, and `2.0.0` above `1.0.0`;
- the v2 checklist keeps actual publication steps unchecked;
- public docs do not claim 2.0.0 has already been published;
- public docs represent the final `--apply`/`--write` artwork boundary correctly.

Tests should not hard-code archive paths to `1.0.0` where the package version is expected to vary; derive the active package version where appropriate while preserving tests for historical v1 facts separately.

## Umbrella v2 Design Correction

The approved Artwork + Audio spec is authoritative for initial v2 BPM sourcing.

Update the old umbrella design where it still says v2 success requires external BPM evidence or local-preferred conflict handling. For the first v2 release:

- there is no external BPM provider;
- Librosa is the only local BPM backend;
- local BPM analysis is optional and disabled by default;
- architecture may admit future `TempoObservation` sources without implementing them now.

This is documentation consistency only, not a behavior change.

## README And Public Capability Summary

README/current public capability text should present v2 behavior accurately while avoiding false publication claims.

It should make clear that the source branch/release candidate includes:

- semantic release/track/artist enrichment;
- CAA artwork;
- optional local BPM;
- ordinary verified file sync;
- existing identity and AcoustID modes.

Published-version links may continue to point to v1.0.0 until v2 publication actually happens.

## Verification Gate

Before the release-readiness PR can be approved, obtain fresh evidence for the exact candidate HEAD:

1. full offline pytest suite;
2. Ruff;
3. repository hygiene;
4. public documentation validator;
5. strict MkDocs build;
6. package build;
7. Twine strict check;
8. distribution content inspection;
9. clean-install package smoke test;
10. dedicated `[audio]` Librosa tests;
11. GitHub CI across Python 3.10-3.14, both beets compatibility lanes, docs, package, and audio-analysis.

Review the final diff against `docs/v2-enrichment-design` and confirm it contains release metadata/docs/tests/contract alignment only, with no unintended functional changes.

## Merge And Release Boundary

Successful completion of this pass authorizes only a recommendation to merge `chore/v2-release-readiness` into `docs/v2-enrichment-design`.

It does not authorize:

- merging the integration branch to `main`;
- creating `v2.0.0`;
- publishing to PyPI;
- changing Read the Docs stable aliases;
- creating a GitHub Release.

Those remain explicit later actions.

## Completion Criteria

The release-readiness phase is complete when:

- `chore/v2-release-readiness` contains only the approved release-contract changes;
- package metadata says `2.0.0`;
- changelog/docs/checklist/tests consistently describe the v2 release candidate without claiming publication;
- stale v1-only permission wording is removed;
- stale external-BPM wording in the umbrella v2 design is corrected;
- all local and GitHub CI verification gates pass;
- no Critical or Important review findings remain.
