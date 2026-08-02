# Handoff

## State

Block 028 and the atime-sensitive test hotfix are complete and merged. Final
`main` CI is green across all supported Python versions and release-validation
jobs. This documentation-only pre-tag update is not Block 029.

## Prepared

- Public English documentation under `site-docs`, with explicit strict MkDocs navigation.
- Pinned Material for MkDocs and version-2 Read the Docs configuration.
- Complete command/config/provider/field/beets/compatibility/troubleshooting references.
- Fresh centralized configuration defaults and release-quality command help.
- Version 1.0.0 package metadata with the owner-selected MIT license and no
  invented author or maintainer.
- Documentation drift checks, archive inspection, and synthetic release workflows.
- Python 3.10-3.14, beets-boundary, docs, package, and hygiene CI jobs.
- Source/wheel `Requires-Python >=3.10,<3.15` release gate; Python 3.15 is not claimed.
- Tag-only build-once OIDC publication workflow with protected `pypi` environment and a local pre-build remote-main ancestry guard after credential-free full-history checkout.
- Canonical changelog/contribution/security documents and explicit owner release checklist.

## Validation

- Final `main` CI passed on Python 3.10-3.14, beets 2.12.0, the latest supported
  beets below 3, documentation, and package validation after the atime-safe test
  hotfix.
- On the hotfix branch, 1,115 offline tests passed and 5 live tests were
  deselected; focused repetition, identity tests, Ruff, docs, hygiene, and
  package gates also passed.
- 165 focused tests passed on beets 2.12.0 and current 2.13.1.
- Python 3.10-3.14 focused release/documentation/plugin smoke tests passed.
- Strict docs, Ruff, hygiene and reachable-history inspection, wheel/sdist,
  Twine, archive inspection, and clean-install plugin help passed.
- 26 focused docs/release tests passed, including license metadata/artifact
  contracts, semantic Python metadata, and static release-workflow contracts.

## Owner-Gate State

Completed and externally confirmed: Block 028 merged after reviewer PASS, the
repository is public, the MIT License is merged, private vulnerability
reporting is enabled, the GitHub `pypi` environment has a `v*` deployment tag
rule, the PyPI Pending Trusted Publisher is configured, the Read the Docs
public `latest` build passed, and final `main` CI is green.

Remaining: merge this documentation-only release-state update, wait for the
resulting `main` CI, create `v1.0.0`, verify the release workflow and first PyPI
publication, create or verify the GitHub Release and versioned Read the Docs
build, and complete post-release checks. The first successful publication will
establish PyPI project ownership.

Tag/version equality alone is insufficient: the release workflow requires the
tagged commit to be contained in remote `main`. Checkout does not persist
credentials; the local ancestry step performs no fetch and fails closed when
`origin/main` is absent. No tag, upload, workflow publication run, or package
publication occurred during Block 028 or its final fixes.

There is no next development block. Do not create Block 029. After this branch
is reviewed and merged, wait for green `main` CI and then create `v1.0.0`.
