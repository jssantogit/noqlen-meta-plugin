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
- [x] Read the Docs project imported, public URL confirmed, and public `latest` build passed.
- [ ] PyPI project ownership established by first publication.
- [x] PyPI Pending Trusted Publisher configured for this repository and `.github/workflows/release.yml`.
- [x] GitHub environment `pypi` configured with the `v*` deployment tag rule.
- [x] Repository security/private vulnerability reporting route confirmed.

## Release Execution

- [x] Block 028 release-candidate branch merged to `main` after reviewer PASS.
- [ ] `v1.0.0` tag created only after reviewer PASS and main merge.
- [ ] Tag version exactly matches `pyproject.toml`.
- [ ] Tag resolves to a commit contained in remote `main`; tag/version equality alone is insufficient.
- [ ] Full-history checkout fetched `origin/main` without persisting credentials; local ancestry validation fails closed if the ref is absent.
- [ ] Tag workflow builds, checks, and publishes the same artifacts through OIDC.
- [ ] No API token or long-lived publishing credential is used.
- [ ] GitHub/PyPI release notes use `CHANGELOG.md` and do not claim external integrations.

## Post-Release Verification

- [ ] PyPI metadata and rendered README are correct.
- [ ] Wheel installs in a clean environment and beets discovers `noqlenmeta`.
- [ ] `beet nm --help` works after the clean install.
- [ ] Published wheel and sdist hashes match the workflow artifacts.
