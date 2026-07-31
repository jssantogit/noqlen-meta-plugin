# Block 028 Design

## Documentation Boundary

`README.md` contains only installation, first preview/apply, concise workflow
boundaries, provider/format/compatibility summaries, and links. `site-docs/` is
the canonical public manual. `mkdocs.yml` points directly to that directory so
internal ADRs, block specs, context, and development policy cannot enter site
output.

MkDocs uses explicit navigation, built-in client-side search, Material light
and dark palettes, code copy controls, no analytics, no remote fonts, and
strict validation. One pinned requirements file serves local, CI, and Read the
Docs builds.

## Interface Source Of Truth

`configuration.default_config()` returns a fresh nested tree and is shared by
plugin initialization and documentation checks. The checker reads real
command parser options, flattens production defaults, validates exact full
YAML parity with duplicate-key detection, checks explicit navigation, limits
README size/content, and scans public pages for required distinctions and
obvious sensitive data.

## Package And CI

Setuptools includes only production Python in the wheel and a deliberately
small source distribution. Distribution validation checks identity, version,
required source, and forbidden runtime/internal content. CI separates the
claimed Python matrix, beets boundary tests, strict documentation, and package
smoke tests.

The release workflow runs only for `v*` tags, verifies an exact semantic tag
match to `pyproject.toml`, builds once in an unprivileged job, uploads checked
artifacts, and publishes those same artifacts in a protected `pypi`
environment using OIDC. No token secret is accepted or configured.

## Product Behavior

Only command help and default placement change in production. Resolution,
provider, importer, database, identity, and filesystem behavior remain
unchanged. Release tests compose existing public boundaries with temporary
beets databases and generated-silence fixtures.
