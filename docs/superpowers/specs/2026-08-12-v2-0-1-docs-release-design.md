# Noqlen Meta v2.0.1 Documentation Release Design

## Goal

Publish a documentation-only patch release, `2.0.1`, that makes the redesigned
Documentation v2 available as the Read the Docs stable release and simplifies the
GitHub/PyPI README into a concise project landing page.

This release must not change Noqlen Meta runtime behavior.

## Context

The Documentation v2 redesign is already merged into `main`, but Read the Docs
`stable` still resolves to the immutable `v2.0.0` tag, whose `mkdocs.yml` and
public pages use the old documentation structure. A new stable patch tag is
therefore needed so the released documentation can include the redesign.

The current README also duplicates manual content that now belongs in Read the
Docs. In particular, its Documentation navigation and First Preview sections are
no longer useful as README content and include links to paths that were replaced
by the Documentation v2 redesign.

## Release Scope

`2.0.1` is a documentation/release-metadata patch only.

Allowed changes:

- simplify `README.md` according to the structure below;
- bump the package version from `2.0.0` to `2.0.1`;
- add a `2.0.1` changelog entry describing documentation and README changes;
- add/update the release checklist for the `2.0.1` release;
- make narrowly required documentation/release-contract test updates caused by
  the version bump or README structure.

The Documentation v2 files already merged to `main` are part of the resulting
`v2.0.1` tag but do not need another redesign in this release.

## README Design

The README is a short landing page, not a second manual.

Its public structure is exactly:

```text
# Noqlen Meta

<short project summary>

## Capabilities

<concise capability list>

## Installation

<installation, optional extras, plugin enablement, verification>
```

No additional top-level README sections are required for this release.

### Summary

The opening summary should explain, in a few short paragraphs, that Noqlen Meta:

- is a beets plugin;
- enriches metadata from multiple providers;
- provides MusicBrainz identity and AcoustID-related workflows in addition to
  ordinary enrichment;
- previews ordinary enrichment by default and keeps mutation explicitly
  authorized.

The summary must stay user-facing. It should not become a detailed explanation
of command modes, internal contracts, or provider architecture.

### Capabilities

The capability list should be compact and cover the product at feature level,
including:

- release, track, and artist enrichment;
- genres, styles, moods, languages, and artist geography;
- lyrics support;
- Cover Art Archive artwork;
- optional local BPM analysis;
- existing-library enrichment;
- MusicBrainz identity audit/repair;
- AcoustID evidence/fingerprint workflows;
- verified database/file synchronization.

Related capabilities should be consolidated rather than expanded into one bullet
per implementation detail.

### Installation

Installation remains practical but does not become a tutorial.

It should include:

```bash
pip install beets-noqlenmeta
```

Optional extras:

```bash
pip install "beets-noqlenmeta[discogs]"
pip install "beets-noqlenmeta[audio]"
```

Plugin enablement:

```yaml
plugins:
  - noqlenmeta
```

And a simple verification command:

```bash
beet help noqlenmeta
```

A brief note may mention that `beet nm` is the preferred alias after the plugin
is loaded. Details about configuration paths, first preview queries, providers,
AcoustID setup, commands, troubleshooting, and workflows belong in Read the
Docs instead.

## README Content Removed

The following content is intentionally removed from the README:

- the published-version/PyPI/GitHub Release block;
- the `Documentation` section and manual navigation links;
- the `First Preview` section;
- the README `License` section;
- detailed configuration-path guidance;
- tutorial-style MusicBrainz/provider configuration.

Removing the README License section does not change the repository or package
license. `LICENSE` and the package metadata remain authoritative.

The README must not hard-code `2.0.1` or future release numbers. Avoiding a
version banner prevents routine patch releases from making the README stale.

## Package And Changelog Versioning

`pyproject.toml` changes only the project version from `2.0.0` to `2.0.1` unless
an existing release contract requires another documentation-only metadata
correction. No dependency, Python, beets, provider, command, or runtime contract
changes are part of this release.

`CHANGELOG.md` receives a dated `2.0.1` entry. It should describe the release as
changed documentation rather than a feature release. Appropriate items include:

- redesigned beginner-first public documentation is now included in the stable
  release tag;
- README reduced to project summary, capabilities, and installation;
- documentation/release metadata corrections included since `2.0.0`.

Do not repeat the full v2 feature list under `2.0.1`.

## Release Checklist

`RELEASE_CHECKLIST.md` should gain a focused `2.0.1` section rather than rewriting
historical completed release records.

The `2.0.1` gate must include:

- package version/changelog consistency;
- README structure/content validation;
- full CI green on the release PR and final `main` commit;
- tag `v2.0.1` created only from a commit contained in `main`;
- release workflow validates the tag/version match;
- PyPI Trusted Publishing succeeds;
- public PyPI version/artifacts are verified;
- GitHub Release `v2.0.1` is created from the published tag and verified;
- Read the Docs recognizes/builds `v2.0.1`;
- `/en/stable/` is verified to resolve to the Documentation v2 content after the
  new stable version is available.

The existing `v2.0.0` tag must remain unchanged.

## Validation And Safety

Production code remains the source of truth. This release must not modify files
under `beetsplug/noqlenmeta`.

Before merge, validation must include the repository's existing gates:

- Ruff;
- offline tests;
- documentation contract validation;
- `mkdocs build --strict`;
- Python 3.10 through 3.14 CI;
- beets 2.12 minimum and latest below 3 compatibility lanes;
- audio/Librosa lane;
- package build, metadata/content inspection, and clean-install smoke test.

Existing validation must not be weakened to accommodate README or version
changes. If an assertion is version-specific, update it to represent `2.0.1`
rather than removing the release guarantee.

The final diff must show no runtime implementation changes.

## Release Flow

The intended sequence is:

```text
release branch
    ↓
README + version + changelog + checklist
    ↓
PR to main
    ↓
full CI green
    ↓
squash merge
    ↓
final main CI green
    ↓
create v2.0.1 tag on that main commit
    ↓
existing Publish Release workflow
    ↓
PyPI verification
    ↓
create and verify GitHub Release v2.0.1
    ↓
Read the Docs v2.0.1/stable verification
```

The existing release workflow remains the publication mechanism. It already
fails closed unless the release tag is contained in `main` and exactly matches
`project.version`.

After successful publication, create the GitHub Release from the existing
`v2.0.1` tag using concise release notes derived from the `2.0.1` changelog entry.

## Non-Goals

This release does not:

- change ordinary enrichment behavior;
- change identity or AcoustID behavior;
- add or remove providers;
- change configuration defaults;
- change dependency ranges other than the package version itself;
- move or retag `v2.0.0`;
- redesign Documentation v2 again;
- make `latest` and `stable` aliases mean the same thing artificially.

## Success Criteria

The release is complete when all of the following are true:

1. README contains only the approved summary, Capabilities, and Installation
   structure.
2. Package and changelog identify version `2.0.1` consistently.
3. No runtime implementation file changed.
4. Release PR and final `main` CI are green.
5. `v2.0.1` is published successfully through the existing trusted release
   workflow.
6. PyPI serves `beets-noqlenmeta==2.0.1` with the simplified README metadata.
7. GitHub Release `v2.0.1` exists and points to the published tag.
8. Read the Docs has a successful `v2.0.1` build and the public `stable` URL
   displays the redesigned Documentation v2 rather than the old v2.0.0 manual.
