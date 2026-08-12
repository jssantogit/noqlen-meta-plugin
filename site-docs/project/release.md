# Release Status

Current stable release: `2.0.1` (2026-08-12).

Noqlen Meta 2.0.1 is published on
[PyPI](https://pypi.org/project/beets-noqlenmeta/), and the corresponding
[GitHub Release](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.1)
uses the `v2.0.1` tag.

Package support is bounded to Python 3.10 through 3.14. Distribution checks
require wheel `Requires-Python` to match `>=3.10,<3.15`; Python 3.15 is not
claimed.

The final `main` CI passed across Python 3.10 through 3.14, the supported beets
compatibility boundaries, documentation, package validation, and the optional
audio-analysis lane. The tagged release workflow then built and validated the
release artifacts and published them through PyPI Trusted Publishing.

## Version 2.0.1

Version 2.0.1 is a documentation-only patch release. It ships the redesigned
beginner-first Documentation v2 as a stable release, reduces the repository and
PyPI README to a concise project landing page, and carries forward documentation
and release-metadata corrections made after 2.0.0. Runtime behavior is unchanged.

## Version 2.0.0

Version 2.0.0 expands Noqlen Meta with semantic release, track, and artist
enrichment; verified artwork handling; optional local BPM analysis; and
existing-library AcoustID workflows. The preview-first safety model and
separate mutation authorities remain intact.

Highlights include:

- lossless multivalued styles and moods;
- lyrics language plus artist language and geography metadata;
- genre taxonomy and style promotion;
- verified ordinary metadata synchronization behind `--apply --write`;
- Cover Art Archive selection, deterministic `cover.jpg` sidecars, multidisc
  reuse, and optional embedding;
- optional local BPM analysis through the `[audio]` extra with lazy Librosa;
- standalone existing-library AcoustID preview and application workflows;
- stored fingerprint reuse and explicit missing-fingerprint calculation through
  `fpcalc` when requested;
- bounded AcoustID lookup using the environment-only
  `NOQLENMETA_ACOUSTID_API_KEY`;
- optional AcoustID compatibility evidence for MusicBrainz identity workflows.

## Publication

The release workflow:

- verifies that the tag version matches `pyproject.toml`;
- proves that the tagged commit is contained in remote `main`;
- checks out complete history without persisting credentials;
- builds wheel and sdist once;
- validates metadata and archive contents;
- publishes the checked artifacts through PyPI Trusted Publishing and OIDC;
- uses no API token or long-lived publishing credential.

## Documentation

The canonical public documentation is live at
[https://noqlen-meta.readthedocs.io/en/stable/](https://noqlen-meta.readthedocs.io/en/stable/).
The Read the Docs project slug is `noqlen-meta`.

The explicit `v2.0.1` Read the Docs version remains a separate post-release
verification item; the `stable` URL above is the canonical public entry point.

The repository root `RELEASE_CHECKLIST.md` remains the operational source for
post-release verification items.

## License

Noqlen Meta is distributed under the MIT License. The canonical license text is
available in the repository root [`LICENSE`](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE).
MIT licensing does not imply endorsement by beets, MusicBrainz, Discogs,
Navidrome, Last.fm, Apple, LRCLIB, AcoustID, or any provider.
