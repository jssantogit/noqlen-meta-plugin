# Handoff

## State

Block 028 implementation is complete. Noqlen Meta 1.0.0 package,
public MkDocs source, concise README, release checks, and publication workflow
have been prepared without adding product behavior.

## Prepared

- Public English documentation under `site-docs`, with explicit strict MkDocs navigation.
- Pinned Material for MkDocs and version-2 Read the Docs configuration.
- Complete command/config/provider/field/beets/compatibility/troubleshooting references.
- Fresh centralized configuration defaults and release-quality command help.
- Version 1.0.0 package metadata with no invented author or license.
- Documentation drift checks, archive inspection, and synthetic release workflows.
- Python 3.10-3.14, beets-boundary, docs, package, and hygiene CI jobs.
- Source/wheel `Requires-Python >=3.10,<3.15` release gate; Python 3.15 is not claimed.
- Tag-only build-once OIDC publication workflow with protected `pypi` environment and a local pre-build remote-main ancestry guard after credential-free full-history checkout.
- Canonical changelog/contribution/security documents and explicit owner release checklist.

## Validation

- 1,105 offline tests passed; 5 live tests were deselected.
- 165 focused tests passed on beets 2.12.0 and current 2.13.1.
- Python 3.10-3.14 focused release/documentation/plugin smoke tests passed.
- Strict docs, Ruff, hygiene, wheel/sdist, Twine, archive inspection, and clean-install plugin help passed.
- 17 focused docs/release tests passed, including semantic Python metadata and static release-workflow contracts.

## External Owner Ceremony

After reviewer PASS and merge, the owner decides/adds licensing (or explicitly
distributes without an open-source grant), imports Read the Docs, confirms PyPI
ownership, configures trusted publishing and the `pypi` environment, creates
the v1.0.0 tag, and verifies GitHub/PyPI/Read the Docs publication.

Tag/version equality alone is insufficient: the release workflow requires the
tagged commit to be contained in remote `main`. Checkout does not persist
credentials; the local ancestry step performs no fetch and fails closed when
`origin/main` is absent. No merge, tag, upload, workflow publication run, or
publication occurred during Block 028 or its final fixes.

There is no next development block. STOP after Block 028 release preparation.
