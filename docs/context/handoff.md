# Handoff

## State

Block 028 received reviewer PASS and was merged. The post-Block-028 owner-gate
change records the MIT decision and prepares package license metadata without
adding product behavior. This is not Block 029.

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

- 1,114 offline tests passed; 5 live tests were deselected.
- 165 focused tests passed on beets 2.12.0 and current 2.13.1.
- Python 3.10-3.14 focused release/documentation/plugin smoke tests passed.
- Strict docs, Ruff, hygiene and reachable-history inspection, wheel/sdist,
  Twine, archive inspection, and clean-install plugin help passed.
- 26 focused docs/release tests passed, including license metadata/artifact
  contracts, semantic Python metadata, and static release-workflow contracts.

## Owner-Gate State

Completed and externally confirmed: Block 028 merged after reviewer PASS,
repository visibility changed to public, and public repository access
confirmed. MIT is selected, the canonical `LICENSE` is added, and PEP 639
package license metadata is prepared.

Still pending: confirm private vulnerability reporting, import and publicly
build Read the Docs, configure the GitHub `pypi` environment, configure the
PyPI pending trusted publisher, establish PyPI project ownership through first
publication, create the `v1.0.0` tag, publish to PyPI, and complete post-release
checks.

Tag/version equality alone is insufficient: the release workflow requires the
tagged commit to be contained in remote `main`. Checkout does not persist
credentials; the local ancestry step performs no fetch and fails closed when
`origin/main` is absent. No merge, tag, upload, workflow publication run, or
publication occurred during Block 028 or its final fixes.

There is no next development block. Do not create Block 029. The next action
after this administrative branch is reviewer audit, followed by the remaining
owner-controlled external ceremony.
