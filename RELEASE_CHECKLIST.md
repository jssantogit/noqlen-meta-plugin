# Noqlen Meta Release Checklist

## Automated And Repository Checks

- [x] Reviewer PASS recorded for the Block 028 release-candidate branch.
- [x] Version, package name, metadata, README, and changelog agree.
- [x] Package and wheel `Requires-Python` are semantically `>=3.10,<3.15`; Python 3.15 is not claimed.
- [x] Full Python and beets compatibility CI is green.
- [x] Final `main` CI atime-sensitive test hotfix prepared without weakening the stale-source guard.
- [x] Offline tests, Ruff, repository hygiene, and diff checks pass locally.
- [x] Public documentation coverage and strict MkDocs build pass locally.
- [x] Wheel and sdist build, Twine, content inspection, and clean-install smoke tests pass locally.
- [x] No generated `site/`, `build/`, `dist/`, egg-info, credential, or private path is committed.

## Owner-Controlled External Checks

- [x] MIT License selected and added with copyright © 2026 João Pedro Rosa dos Santos.
- [x] Repository visibility changed to public and public access confirmed.
- [x] Read the Docs project imported and public `latest`, `stable`, and `v1.0.0` builds passed.
- [x] PyPI project ownership established by the first successful publication.
- [x] PyPI Trusted Publisher configured for this repository and `.github/workflows/release.yml` and used successfully.
- [x] GitHub environment `pypi` configured with the `v*` deployment tag rule.
- [x] Repository security/private vulnerability reporting route confirmed.

## Release Execution

- [x] Block 028 release-candidate branch merged to `main` after reviewer PASS.
- [x] `v1.0.0` tag created only after reviewer PASS and main merge.
- [x] Tag version exactly matches `pyproject.toml`.
- [x] Tag resolves to a commit contained in remote `main`; tag/version equality alone is insufficient.
- [x] Full-history checkout fetched `origin/main` without persisting credentials; local ancestry validation failed closed if the ref was absent.
- [x] Tag workflow built, checked, and published the same artifacts through OIDC.
- [x] No API token or long-lived publishing credential was used.
- [x] GitHub/PyPI release notes use `CHANGELOG.md` and do not claim external integrations.

## Post-Release Verification

- [x] PyPI project name, version, `Requires-Python`, filenames, and file count are correct.
- [ ] PyPI rendered README has been visually reviewed.
- [ ] Public wheel installs in a clean environment and beets discovers `noqlenmeta`.
- [ ] `beet nm --help` works after the public clean install.
- [x] Published wheel and sdist hashes match the workflow artifacts attached to the GitHub Release.
- [x] GitHub Release `v1.0.0` was created from the existing tag.
- [x] Read the Docs `stable`, `latest`, and `v1.0.0` versions are active and green.

## Version 2.0.0 Release

### Candidate Preparation

- [x] Package version is `2.0.0`.
- [x] Changelog contains `2.0.0 - 2026-08-11`.
- [x] Full offline test suite and Ruff pass.
- [x] Python 3.10 through 3.14 CI matrix passes.
- [x] beets 2.12.0 and latest below 3 compatibility lanes pass.
- [x] `[audio]` Librosa test lane passes.
- [x] Public documentation validation and strict MkDocs build pass.
- [x] Package build, strict Twine check, distribution inspection, and clean-install smoke test pass.
- [x] Release-readiness diff contains no unintended functional feature work.

### Owner-Authorized Release Execution

- [x] Merge the v2 release candidate into `main`.
- [x] Confirm final `main` CI.
- [x] Create `v2.0.0` tag on a commit contained in `main`.
- [x] Allow the tag workflow to build and publish through PyPI Trusted Publishing.
- [x] Create and verify the GitHub Release for `v2.0.0`.
- [x] Publish `2.0.0` to PyPI and verify its artifacts.
- [x] Confirm the canonical Read the Docs project at `noqlen-meta.readthedocs.io` and the public `stable` URL.
- [ ] Verify the explicit versioned Read the Docs `v2.0.0` build, if retained as a public version.

### Post-Release Follow-up

- [ ] Visually review the PyPI-rendered README for `2.0.0`.
- [ ] Install `beets-noqlenmeta==2.0.0` in a fresh environment and confirm beets discovers `noqlenmeta`.
- [ ] Run `beet nm --help` from that public clean installation.

## Version 2.0.1 Documentation Release

### Candidate Preparation

- [x] Package version is `2.0.1`.
- [x] Changelog contains `2.0.1 - 2026-08-12`.
- [x] README contains only the approved summary, Capabilities, and Installation structure.
- [x] README contains no release-version banner, Documentation section, First Preview section, or License section.
- [x] Documentation v2 remains the public MkDocs information architecture.
- [x] Release-readiness diff contains no changes under `beetsplug/noqlenmeta`.
- [x] Full CI is green on the release pull request.

### Owner-Authorized Release Execution

- [ ] Merge the `2.0.1` release candidate into `main`.
- [ ] Confirm final `main` CI.
- [ ] Create `v2.0.1` tag on a commit contained in `main`.
- [ ] Allow the existing tag workflow to verify the tag/version match and publish through PyPI Trusted Publishing.
- [ ] Publish `2.0.1` to PyPI through Trusted Publishing.
- [ ] Create and verify the GitHub Release for `v2.0.1`.

### Post-Release Verification

- [ ] Verify the public PyPI `2.0.1` metadata and artifacts.
- [ ] Visually review the PyPI-rendered simplified README.
- [ ] Read the Docs builds `v2.0.1` successfully.
- [ ] `/en/stable/` displays the redesigned Documentation v2 rather than the old v2.0.0 manual.
- [ ] Public `beets-noqlenmeta==2.0.1` clean install discovers `noqlenmeta` and `beet nm --help` works.
