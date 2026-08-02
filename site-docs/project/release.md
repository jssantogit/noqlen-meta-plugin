# Release Status

Noqlen Meta 1.0.0 is prepared as a release candidate. Repository validation
can complete without external publication.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; v1.0.0 does not claim
Python 3.15 support.

Block 028 received reviewer approval and was merged. The GitHub repository is
public and public access has been confirmed. The MIT License was selected, and
the repository's root
[`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)
is the canonical license text.

Remaining owner-controlled work includes Read the Docs project import and
public build confirmation, private vulnerability reporting confirmation, a
protected `pypi` environment, PyPI pending trusted-publisher configuration,
creation of `v1.0.0`, first publication establishing PyPI project ownership,
and post-release checks. A public GitHub repository does not mean that Read the
Docs is live or that the package is published on PyPI.

The release workflow requires both an exact tag/version match and proof that
the tagged commit is contained in remote `main`. Tag/version equality alone is
not sufficient to publish. Authenticated checkout obtains complete branch and
tag history with `fetch-depth: 0` but does not persist credentials. The later
ancestry check is fully local, requires `refs/remotes/origin/main` to exist,
and fails closed without a post-checkout network Git command.

The implementation branch does not merge itself, create a tag, publish a
GitHub release, upload to PyPI, create credentials, or configure Read the Docs.
The repository root `RELEASE_CHECKLIST.md` is the operational source for those
gates and is intentionally not duplicated here.

MIT licensing does not imply endorsement by beets, MusicBrainz, Discogs,
Navidrome, Last.fm, Apple, LRCLIB, or any provider.
