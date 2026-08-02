# Release Status

Noqlen Meta 1.0.0 is ready for the release tag. Repository validation can
complete without external publication.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; v1.0.0 does not claim
Python 3.15 support.

Block 028 received reviewer approval and was merged. The GitHub repository is
public and public access has been confirmed. The MIT License was selected, and
the repository's root
[`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)
is the canonical license text.

Completed external setup:

- public repository;
- MIT License;
- private vulnerability reporting;
- GitHub `pypi` environment with the `v*` deployment tag rule;
- PyPI Pending Trusted Publisher for this repository and release workflow;
- Read the Docs import and successful public `latest` build.

The canonical public documentation is live at
[https://noqlen-meta-plugin.readthedocs.io/](https://noqlen-meta-plugin.readthedocs.io/).

Pending release work:

- final `main` CI confirmation;
- creation of the `v1.0.0` tag;
- first PyPI publication, which will establish project ownership;
- post-publication artifact verification.

The package has not been published to PyPI. A versioned Read the Docs `v1.0.0`
build does not exist before the tag is created and built.

The release workflow requires both an exact tag/version match and proof that
the tagged commit is contained in remote `main`. Tag/version equality alone is
not sufficient to publish. Authenticated checkout obtains complete branch and
tag history with `fetch-depth: 0` but does not persist credentials. The later
ancestry check is fully local, requires `refs/remotes/origin/main` to exist,
and fails closed without a post-checkout network Git command.

This administrative branch does not merge itself, create a tag, publish a
GitHub release, or upload to PyPI. The repository root `RELEASE_CHECKLIST.md`
is the operational source for those gates.

MIT licensing does not imply endorsement by beets, MusicBrainz, Discogs,
Navidrome, Last.fm, Apple, LRCLIB, or any provider.
