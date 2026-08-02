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
