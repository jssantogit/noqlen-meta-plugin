# Block 028 Requirements

## Goal

Prepare Noqlen Meta 1.0.0 as an installable, beginner-friendly, documented,
auditable release candidate without adding metadata/provider behavior or
performing external publication.

## Product And Package

- Use the public name Noqlen Meta and accurate matcher/enrichment positioning.
- Set package version 1.0.0 and claim only tested Python/beets compatibility.
- Keep Discogs optional and add no runtime dependency unrelated to production.
- Do not invent author, maintainer, license, OS, or feature metadata.
- Validate wheel, sdist, rendered README, discovery, and clean installation.

## Public Documentation

- Keep README below 500 lines as the GitHub/PyPI landing page.
- Publish only `site-docs` through explicit strict MkDocs navigation.
- Use pinned Material for MkDocs and a version-2 Read the Docs configuration.
- Cover getting started, concepts, guides, complete reference,
  troubleshooting, advanced safety/architecture, and project status.
- Distinguish importer, ordinary database, identity database, native beets
  write, and identity-tag file authorities.
- Check every public long option and configuration leaf against production.

## Validation And Release Safety

- Add synthetic release workflows and bounded performance/ordering sanity.
- Test Python 3.10-3.14 and minimum/latest compatible beets in CI.
- Build documentation strictly and inspect package contents in CI.
- Prepare a tag-only OIDC trusted-publishing workflow that builds once.
- Record license, Read the Docs, PyPI ownership, environment, trusted
  publisher, tag, and publication as owner gates.
- Do not merge, tag, upload, publish, create credentials, or touch real music.
