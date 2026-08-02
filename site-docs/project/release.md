# Release Status

Noqlen Meta 1.0.0 was released on 2026-08-02. The package is published on
[PyPI](https://pypi.org/project/beets-noqlenmeta/), and the corresponding
[GitHub Release](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v1.0.0)
uses the existing `v1.0.0` tag.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; v1.0.0 does not claim
Python 3.15 support.

Block 028 received reviewer approval and was merged. Final `main` CI passed
across Python 3.10 through 3.14, the supported beets compatibility boundaries,
documentation, and package validation. The GitHub repository is public, the
root [`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)
is the canonical MIT License text, and private vulnerability reporting is
enabled.

## Publication

The release workflow:

- verified that the tag version matched `pyproject.toml`;
- proved that the tagged commit was contained in remote `main`;
- checked out complete history without persisting credentials;
- built wheel and sdist once;
- validated metadata and archive contents;
- published the checked artifacts through PyPI Trusted Publishing and OIDC;
- used no API token or long-lived publishing credential.

PyPI project ownership was established by the first successful publication.
The published wheel and sdist hashes match the workflow artifacts attached to
the GitHub Release.

## Documentation

The canonical public documentation is live at
[https://noqlen-meta-plugin.readthedocs.io/](https://noqlen-meta-plugin.readthedocs.io/).
The `latest`, `stable`, and versioned `v1.0.0` builds are active and green.
Version 1.0.0 is also available directly at
[https://noqlen-meta-plugin.readthedocs.io/en/v1.0.0/](https://noqlen-meta-plugin.readthedocs.io/en/v1.0.0/).

## Remaining Verification

The release itself is complete. The operational checklist still leaves two
local consumer checks explicit until they are run against the public package:

- install `beets-noqlenmeta==1.0.0` in a fresh environment and confirm beets
  discovers `noqlenmeta`;
- run `beet nm --help` from that public clean installation.

The repository root `RELEASE_CHECKLIST.md` is the operational source for these
post-release checks.

MIT licensing does not imply endorsement by beets, MusicBrainz, Discogs,
Navidrome, Last.fm, Apple, LRCLIB, or any provider.
