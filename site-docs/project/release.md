# Release Status

Noqlen Meta 1.0.0 is prepared as a release candidate. Repository validation
can complete without external publication.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; v1.0.0 does not claim
Python 3.15 support.

Block 028 received reviewer approval and was merged. The owner selected the
MIT License and public repository visibility. The repository's root
[`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE)
is the canonical license text. Public visibility remains an external gate and
is not complete until GitHub reports that public access is available.

Publication remains owner-controlled and requires Read the Docs project
import, PyPI ownership and trusted-publisher configuration, a protected
`pypi` environment when used, and creation of `v1.0.0` only after those gates.

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
