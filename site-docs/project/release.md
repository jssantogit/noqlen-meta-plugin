# Release status

**Current published package release: `3.0.0` (2026-10-30).**

[Noqlen Meta v3.0.0](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v3.0.0)
is a published GitHub Release. The `v3.0.0` tag points to the exact approved
`main` commit `3ae7fb6da812a5ba1a27d7525571293d7be225e1`.
The tagged [Publish Release workflow](https://github.com/jssantogit/noqlen-meta-plugin/actions/runs/41045690976)
completed with successful build and PyPI Trusted Publishing jobs.

Install the current published distribution from
[PyPI](https://pypi.org/project/beets-noqlenmeta/):

```bash
pip install --upgrade beets-noqlenmeta
```

## What's new in 3.0.0?

- Typed MusicBrainz Recording/Work identity references, scoped structured
  composer/lyricist/producer/performer credits and provenance.
- Additional recording metadata: instrumental state, explicit/clean advisory,
  alternative titles/transliterations, typed version/mix, and opt-in
  conservative `vocal_languages`.
- Synchronized lyrics through guarded `.lrc` sidecars, plus exact-release
  Back artwork through guarded `back.jpg` sidecars.
- Optional local Key and versioned 0–1 Energy and Danceability **signal/rhythm
  proxies**; not validated perceptual or Spotify-equivalent scores.
- Existing V2 defaults remain unchanged. Preview/apply/write safety boundaries,
  DB-only fields, no-clobber behavior and conservative unknown handling remain.

**Outside 3.0.0:** direct spoken/sung-language recognition from audio and
individual CD/Medium surface artwork.

For full details, see the [Changelog](changelog.md),
[V3 enrichment recipe](../recipes/v3-enrichment.md), and
[Field Reference](../technical-reference/fields.md).

## Compatibility

Python **3.10 through 3.14** and `beets>=2.12,<3` are supported by the
CI matrix. Python 3.15 is not claimed; package metadata declares
`Requires-Python >=3.10,<3.15`. Package build, strict metadata validation,
clean-install smoke, documentation, optional audio analysis and both beets
compatibility boundaries passed before release.

## Documentation versions and deployment

The canonical public documentation is live at
[https://noqlen-meta.readthedocs.io/en/stable/](https://noqlen-meta.readthedocs.io/en/stable/).
The Read the Docs project slug is `noqlen-meta`.

Read the Docs builds `latest` from the default `main` branch. Its `stable`
alias resolves to the newest **active** stable semver Git tag; by design, a
versioned build remains a snapshot of that tag. A documentation change merged
to `main` updates `latest`, **not the previously released `v3.0.0` source
snapshot**. If the new tag is not active, activate it in the project's
**Versions** dashboard and verify its build. Changes merged after `v3.0.0`
will reach `stable` in a subsequent tagged documentation or patch release.

Repository `RELEASE_CHECKLIST.md` records the external Read the Docs version
and public installation checks separately; GitHub Actions success alone does
not verify the live Read the Docs alias.

## Previous releases

- [2.0.1 (2026-08-12)](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.1):
  documentation-focused patch, no runtime behavior changes.
- [2.0.0 (2026-08-11)](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v2.0.0):
  semantic metadata, Cover Art Archive front covers, local BPM, and AcoustID.
- [1.0.0 (2026-08-02)](https://github.com/jssantogit/noqlen-meta-plugin/releases/tag/v1.0.0):
  initial public release.

## Licensing and publication integrity

The canonical MIT License text is [MIT](https://github.com/jssantogit/noqlen-meta-plugin/blob/main/LICENSE).
MIT licensing does not imply endorsement by any provider or beets itself.

The tagged release workflow verifies `main` ancestry and tag/package
version, builds wheel and sdist, checks package contents, and publishes via
PyPI Trusted Publishing (OIDC) without a long-lived PyPI token. Public wheel
installation and Read the Docs build status are independent verification steps.
