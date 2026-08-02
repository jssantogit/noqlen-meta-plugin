# Release Status

Noqlen Meta 1.0.0 is prepared as a release candidate. Repository validation
can complete without external publication.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; v1.0.0 does not claim
Python 3.15 support.

Publication remains owner-controlled and requires reviewer approval and merge,
an explicit license decision, Read the Docs project import, PyPI ownership and
trusted-publisher configuration, a protected `pypi` environment when used, and
creation of `v1.0.0` only after those gates.

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
