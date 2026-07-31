# Noqlen Meta Release Checklist

## Automated And Repository Checks

- [ ] Reviewer PASS recorded for the release-candidate branch.
- [ ] Version, package name, metadata, README, and changelog agree.
- [ ] Full Python and beets compatibility CI is green.
- [ ] Offline tests, Ruff, repository hygiene, and diff checks pass.
- [ ] Public documentation coverage and strict MkDocs build pass.
- [ ] Wheel and sdist build once, pass Twine, content inspection, and clean-install smoke tests.
- [ ] No generated `site/`, `build/`, `dist/`, egg-info, credential, or private path is committed.

## Owner-Controlled External Checks

- [ ] The repository owner selected and added the intended license, or explicitly decided to distribute without granting an open-source license.
- [ ] Read the Docs project imported and public URL confirmed.
- [ ] PyPI project/package ownership confirmed.
- [ ] PyPI trusted publisher configured for this repository and `.github/workflows/release.yml`.
- [ ] GitHub environment `pypi` configured when used, with appropriate protection.
- [ ] Repository security/private vulnerability reporting route confirmed.

## Release Execution

- [ ] Release-candidate branch merged to `main` only after reviewer PASS.
- [ ] `v1.0.0` tag created only after reviewer PASS and main merge.
- [ ] Tag version exactly matches `pyproject.toml`.
- [ ] Tag workflow builds, checks, and publishes the same artifacts through OIDC.
- [ ] No API token or long-lived publishing credential is used.
- [ ] GitHub/PyPI release notes use `CHANGELOG.md` and do not claim external integrations.

## Post-Release Verification

- [ ] PyPI metadata and rendered README are correct.
- [ ] Wheel installs in a clean environment and beets discovers `noqlenmeta`.
- [ ] `beet nm --help` works after the clean install.
- [ ] Read the Docs canonical public build succeeds.
- [ ] Published wheel and sdist hashes match the workflow artifacts.
