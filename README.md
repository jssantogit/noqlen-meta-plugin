# Noqlen Meta Plugin

Universal metadata enrichment for beets.

Noqlen Meta is a beets plugin focused on enriching an already identified release with broader, field-aware metadata from multiple providers. The goal is not to replace beets' matcher. Beets remains responsible for release identification and import flow; Noqlen Meta adds a provider orchestration layer, field authority, conflict resolution, provenance, and reviewable enrichment.

## Project direction

```text
providers
    ↓
normalized candidates
    ↓
Field Authority
    ↓
FieldDecision
    ↓
ChangePlan
    ↓
BeetsTargetPlan
    ↓
explicit application policy
    ↓
selected AlbumInfo mutation
    ↓
normal beets lifecycle
```

`ChangePlan` describes what Noqlen would change and what still requires review. It does not write
metadata. `BeetsTargetPlan` then determines whether each canonical change can be represented by the
current beets `AlbumInfo` model without information loss. Noqlen maps canonical values to beets only
when the mapping is lossless. Multi-value metadata is not silently collapsed into singular beets
fields. With explicit application enabled, the strict default requires a review-free and fully
lossless target plan. An explicitly configured partial policy may instead apply only the already
resolved, losslessly mapped subset. Both policies mutate only the selected `AlbumInfo`; beets then
remains responsible for its normal import lifecycle.

```text
genres = [Rock, Metal]          -> genres (lossless)
labels = [Label A, Label B]     -> mapping blocker
```

The first providers are expected to include MusicBrainz, Discogs, and AcoustID, followed by additional catalog, community, lyrics, and fallback sources where they add clear value.

## Development model

This repository follows the Noqlen Playbook workflow:

```text
Plan → Block → Prompt → Tool Mode → Implement → Validate → Audit → Fix → Commit → Handoff → Next block
```

For provider integrations, this project uses the repository's **real-first, fixture-backed** fast path. Production adapters are implemented directly, external I/O stays behind narrow boundaries, representative real responses may be sanitized into fixtures, normal tests remain offline and deterministic, live tests are opt-in, and failure-only mocks are used where reproducing failures against a real service would be wasteful or unsafe.

Automated tests must never use a real music library.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
ruff check .
python scripts/check_repo_contamination.py
```

Enable the plugin in a beets configuration after installing it into the same Python environment:

```yaml
plugins:
  - noqlenmeta

noqlenmeta:
  preview: true
  apply: false
  apply_mode: strict

  fields:
    genres: true
    styles: true
    labels: true
    catalog_numbers: true
    barcodes: true
    country: true
    year: true
    media: true
    format_descriptions: true
    mood: false
    lyrics: false
    synced_lyrics: false
    cover: false

  providers:
    discogs:
      enabled: false
      user_token: ""

    itunes:
      enabled: false
      storefront: "us"
```

`fields` controls what Noqlen may enrich. `providers` controls where Noqlen may obtain metadata. Both
providers are disabled by default and can be enabled independently or simultaneously. Discogs is
catalog- and edition-oriented. iTunes is currently a fallback only for the narrow album genre and
release year metadata exposed with defensible semantics. Field Authority determines the winner when
both providers return a candidate; higher provider-local confidence alone does not override a more
authoritative source.

`apply` is `false` by default, and `apply_mode` defaults to `strict`. With `apply: false`, Noqlen
never mutates the selected release. With `apply: true`, strict mode applies only when the entire
target plan is lossless and has no resolver `REVIEW`; any review or mapping blocker prevents every
Noqlen mutation. Partial mode requires explicit `apply_mode: partial` and may apply only losslessly
mapped, already-resolved changes while review and mapping-blocked fields are withheld and remain
visible in preview.

Partial mode never accepts a `REVIEW`, selects a review candidate, serializes or reduces a mapping
blocker, or continues after an application contract error. All eligible mapped changes remain one
atomic subset: target-plan integrity, stale state, target shapes, and target uniqueness are fully
validated before any mutation. A failure aborts the whole mapped subset.

For example, genres `Rock, Metal` map losslessly while labels `Label A, Label B` produce a mapping
blocker. Strict mode applies zero fields. Partial mode applies genres and withholds labels; it does
not discard or serialize the label values. `preview` and `apply` are independent, so preview can be
disabled without disabling application and preview output never implies application.

## Library preview command

Noqlen Meta can preview enrichment for albums already stored in the beets library:

```bash
beet nm artist:Gojira
beet nm album:"From Mars to Sirius"
beet nm --all
```

The canonical command name is `beet noqlenmeta ...`; `nm` is its preferred short alias. A non-empty
native beets album query is required unless `--all` explicitly requests every album. The command
operates on albums only; singleton and per-track command modes are not available.

Block 013's library command is preview-only. It runs the same provider collection, Field Authority,
resolver, and `ChangePlan` path as importer enrichment, then analyzes the result against an explicit
persistent `Album` target map. Losslessly representable changes, resolver reviews, and mapping
blockers are displayed without changing database rows, Items, tags, or files. In particular,
persistent `Album` has no album-level `media` field, so media proposals are reported as blockers
rather than being inferred from or applied to Items.

`noqlenmeta.apply` and `apply_mode` currently control importer-time selected-release application
only; they do not make `beet nm` write to the library. The explicit library preview also remains
visible when importer `preview` is false. There is no `--apply` option in Block 013.

Noqlen mutates only eligible fields on the selected `AlbumInfo`. It does not directly mutate Items or
Albums, add library records, write tags, or move/copy files. After selected-release enrichment,
normal beets import behavior determines Item application, database persistence, file handling, and
tag writing. Consequently, `apply: true` is a real metadata application feature: the normal import
can persist enriched values to the beets library and, depending on beets configuration, file
metadata.

Field Authority expresses provider preference and ordering for each field. Provider Capabilities
describe the fields each current adapter can actually produce. An enabled provider is contacted only
when its capabilities intersect both enabled user fields and its Field Authority entries; authority
may retain future fallback vocabulary that an adapter does not implement yet.

Set `providers.discogs.enabled: true` to preview resolved Discogs decisions after selecting an album
match. A non-empty `NOQLENMETA_DISCOGS_TOKEN` takes precedence over
`providers.discogs.user_token`; direct Discogs release-ID lookups do not require a token. Tokens are
redacted and never included in preview output.

Set `providers.itunes.enabled: true` to use Apple's public iTunes Search API for album enrichment.
`storefront` is a two-letter search territory such as `us`, `br`, `gb`, or `jp`. iTunes requests are
bounded to at most 10 album search results, and direct collection-ID or UPC lookup is preferred when
available. No API key is required. No artwork or previews are requested or consumed. iTunes store
country is not treated as release-country metadata, and the provider does not claim label, catalog
number, or barcode metadata.

The pre-release `noqlenmeta.discogs` configuration from Block 004 has been replaced rather than
retained as a parallel schema. Move its values under `noqlenmeta.providers.discogs`.

The target-plan preview reports application state while normal beets metadata application continues
unchanged:

```text
Noqlen Meta / beets target plan:

  application: disabled (preview only)
  planned changes: 1
  losslessly mapped: 1
  mapping blockers: 0
  resolution review: 0
  unchanged: 0
  skipped: 0
  mapping complete: yes

  genres
    PROPOSE
    target: genres
    target shape: string-list
    proposed: Electronic, Rock
    source: Discogs
    confidence: 0.92
    reason: selected 'discogs' by field authority; current value is missing
```

## Current status

The plugin resolves Discogs and iTunes candidates through one shared planning path. Importer
enrichment maps the resulting `ChangePlan` to `BeetsTargetPlan`; the read-only library command maps
it to `LibraryTargetPlan`. Importer application can mutate only selected `AlbumInfo` under its
explicit strict or partial policy. The library command performs no application or persistence.

See `docs/context/current.md` and `docs/context/handoff.md` before starting a development block.
