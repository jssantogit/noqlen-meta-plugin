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

    musicbrainz:
      enabled: false

    lastfm:
      enabled: false

    itunes:
      enabled: false
      storefront: "us"

    lrclib:
      enabled: false

  # Optional advanced resolution overrides. Omitted fields keep built-in defaults.
  resolution:
    authority:
      genres:
        - discogs
        - lastfm
        - itunes
      year:
        - musicbrainz
        - discogs
        - itunes

    min_confidence:
      genres: 0.80
      year: 0.90

    preserve_existing:
      genres: true
      year: false
```

`fields` controls what metadata Noqlen wants. `providers` controls where metadata may come from.
`resolution.authority` controls the preferred provider order per field,
`resolution.min_confidence` controls the field-level eligibility threshold, and
`resolution.preserve_existing` controls whether an existing conflict requires review. Every advanced
setting is optional; empty mappings use the built-in defaults.

A configured authority list replaces the default order for that field; it does not merge with or
prepend to the default. An omitted field keeps its built-in default. The first provider is highest
authority, and a lower-authority candidate cannot win merely because its numeric confidence is
higher. Authority does not imply provider capability. A provider listed for a field is queried only
if it is enabled and its adapter currently declares support for that field.

All providers are disabled by default and can be enabled independently or simultaneously. Discogs
is catalog- and edition-oriented. MusicBrainz enriches only from an exact MusicBrainz release MBID
already known by beets; it does not perform fuzzy release matching. Last.fm currently contributes
album genres only. iTunes is currently a fallback only for the narrow album genre and release year
metadata exposed with defensible semantics.

`apply` is `false` by default, and `apply_mode` defaults to `strict`. With `apply: false`, Noqlen
never mutates the selected release. With `apply: true`, strict mode applies only when the entire
target plan is lossless and has no resolver `REVIEW`; any review or mapping blocker prevents every
Noqlen mutation. Partial mode requires explicit `apply_mode: partial` and may apply only losslessly
mapped, already-resolved changes while review and mapping-blocked fields are withheld and remain
visible in preview.

`preserve_existing: false` can turn a conflicting existing value from `REVIEW` into `PROPOSE`, but
it never grants write permission by itself. Importer writes still require `apply: true`, and library
CLI writes still require `--apply`; all existing strict or partial application checks continue to
apply.

Partial mode never accepts a `REVIEW`, selects a review candidate, serializes or reduces a mapping
blocker, or continues after an application contract error. All eligible mapped changes remain one
atomic subset: target-plan integrity, stale state, target shapes, and target uniqueness are fully
validated before any mutation. A failure aborts the whole mapped subset.

For example, genres `Rock, Metal` map losslessly while labels `Label A, Label B` produce a mapping
blocker. Strict mode applies zero fields. Partial mode applies genres and withholds labels; it does
not discard or serialize the label values. `preview` and `apply` are independent, so preview can be
disabled without disabling application and preview output never implies application.

## Track-level lyrics

Noqlen distinguishes release and track enrichment contexts internally. Existing Discogs,
MusicBrainz, Last.fm, and iTunes providers remain release-scoped. Read-only track identity adapters
can represent selected `TrackInfo` and persistent `Item` metadata, including duration, track/disc
position, MusicBrainz recording and release-track IDs, ISRCs, and AcoustID track IDs.

LRCLIB is the first track-scoped Noqlen provider and supports plain and synchronized lyrics. It uses
the selected track title, artist, album, and duration for an exact-signature `GET /api/get` lookup.
Album title and duration must be available before a request is made, and LRCLIB applies approximately
a +/-2 second duration matching tolerance. No API key is required.

Noqlen does not fall back to LRCLIB search when the exact track signature is unavailable or not
found. Beets decides which track it is; LRCLIB only enriches that selected identity. Raw lyrics are
never logged by the provider, and fixture/test lyrics are synthetic.

During an accepted importer match, Noqlen can build a track plan for each selected
`AlbumMatch` Item/`TrackInfo` pair or for the selected singleton `TrackMatch`. Album extras and
unmatched tracks are excluded. Track planning runs when preview or application is enabled and an
enabled track-scoped provider can contribute to an enabled field under the configured authority.
LRCLIB is currently the only such provider. Its adapter is created lazily and retained by the plugin
so its in-process cache, pacing, and Retry-After state are shared across selected tracks.

The track resolver baseline predicts the canonical values that normal beets 2.12.x metadata
application will produce before any Noqlen candidate is considered:

- For an album match, selected metadata is `TrackInfo.merge_with_album(AlbumInfo)`.
- For a singleton, selected metadata is `TrackInfo.item_data`.
- With `from_scratch: false`, Item-local canonical values form the baseline and selected metadata is
  overlaid on it.
- With `from_scratch: true`, the baseline mirrors `Item.clear()`: modeled writable media fields are
  cleared, flexible metadata survives, and selected metadata is then overlaid.

For the current fields, this means `lyrics` is cleared by `from_scratch: true` when selected metadata
omits it, while the flexible `synced_lyrics` value survives. Selected overlay is presence-sensitive: a
field absent from beets' application mapping leaves the baseline untouched, while a present empty or
non-canonical value still overwrites the Item and removes that canonical current value. This behavior
is covered by parity tests that invoke real `AlbumMatch.apply_metadata()` and
`TrackMatch.apply_metadata()` for both fields, both `from_scratch` modes, and absent, non-empty, empty,
or whitespace-only selected values.

Track plans reuse the existing Field Authority, resolver, and `ChangePlan`, then analyze already
proposed canonical changes through a separate `TrackTargetPlan`:

```text
LRCLIB
  -> canonical lyrics / synced_lyrics
  -> ChangePlan
  -> TrackTargetPlan
  -> safe preview
```

Plain `lyrics` has one lossless selected target: `TrackInfo.lyrics`. Canonical lyric content and
internal newlines are preserved exactly. `synced_lyrics` instead produces a visible mapping blocker
because normal beets does not model it as an equivalent standard persistent Item field. The beets
Lyrics plugin stores canonical synchronized LRC text in `Item.lyrics` and passes native SYLT data
separately during file writing. Synchronized lyrics are not silently collapsed into plain lyrics or
stored as an arbitrary flexible field.

With importer `apply: true`, Noqlen may now mutate only losslessly mapped selected `TrackInfo`
fields. It does not directly update Items, store database rows, or write files; normal beets applies
the selected metadata later in its importer lifecycle. The current writable mapping is only
`lyrics -> TrackInfo.lyrics`. `synced_lyrics` remains unsupported and mapping-blocked.

Strict mode is the default and prevents every Noqlen change for one selected track when that track
has any resolver review or mapping blocker. Explicit partial mode may prepare already-resolved,
losslessly mapped fields while reviews and blockers are withheld. It never accepts a review or
converts synchronized lyrics. Each selected track is validated and applied independently, including
target-plan integrity, effective-current stale state, target shape, and target uniqueness. Cached
`TrackInfo.raw_data` and `TrackInfo.item_data` views are invalidated after successful mutation so
normal later beets application observes the new metadata.

Noqlen does not call `AlbumMatch.apply_metadata()` or `TrackMatch.apply_metadata()`. Downstream beets
may later persist or write plain lyrics as part of normal import; Noqlen itself does not call Item
storage or file-writing APIs. Preview displays only character and line counts for current and
candidate lyric values; raw plain or synchronized lyrics are never rendered.

### Execution matrix

| Entry point and settings | Release behavior | Track behavior | Noqlen write boundary |
| --- | --- | --- | --- |
| Importer, `preview: true`, `apply: false` | Preview eligible release plans | Preview eligible selected-track plans; LRCLIB may run | No mutation |
| Importer, `preview: true`, `apply: true` | Guarded strict/partial selected `AlbumInfo` application plus preview | Guarded strict/partial selected `TrackInfo` application plus preview | Selected `AlbumInfo` and selected `TrackInfo` only |
| Importer, `preview: false`, `apply: true` | Guarded release application without preview | Guarded track application without preview; LRCLIB may run | Selected `AlbumInfo` and selected `TrackInfo` only |
| Importer, `preview: false`, `apply: false` | No release work | No track work | No mutation |
| `beet noqlenmeta` / `beet nm` | Existing album query preview or explicit database application | No singleton or per-track mode; LRCLIB is not called | Existing persistent Album policy only |
| File tag synchronization | No new behavior | No track synchronization | No new behavior |

## Library command

Noqlen Meta previews enrichment for albums already stored in the beets library by default:

```bash
beet nm artist:Gojira
beet nm album:"From Mars to Sirius"
beet nm --all
```

Explicit application persists eligible metadata to the beets library database. Strict mode remains
the default, while partial mode must be explicitly requested:

```bash
beet nm artist:Gojira --apply
beet nm artist:Gojira --apply --partial
beet nm --all --apply
beet nm --all --apply --partial
```

The canonical command name is `beet noqlenmeta ...`; `nm` is its preferred short alias. A non-empty
native beets album query is required unless `--all` explicitly requests every album. The command
operates on albums only; singleton and per-track command modes are not available.

The command runs the same provider collection, Field Authority, resolver, and `ChangePlan` path as
importer enrichment, then analyzes the result against an explicit persistent `Album` target map.
Without `--apply`, it displays losslessly representable changes, resolver reviews, and mapping
blockers without changing database rows, Items, tags, or files.

`--apply` is the only CLI write permission, and `--partial` is invalid without it. Importer
`noqlenmeta.apply` and `apply_mode` settings do not authorize or select CLI writes: command mode
comes only from `--apply` and `--partial`. Importer `apply: true` cannot make a preview command write,
and importer `apply: false` does not override explicit CLI application.

With `--apply` alone, strict mode prevents every Noqlen database change for an Album when any
resolver `REVIEW` or library mapping blocker exists. With `--apply --partial`, losslessly mapped and
resolved fields may persist together while review and mapping-blocked fields remain unchanged and
visible. Partial mode is classification before application, not best-effort exception recovery. The
entire mapped subset is atomically validated for canonical plan integrity, local dirty state, fresh
persisted before-state, target shape, and target uniqueness before any mutation. Stale or malformed
mapped data aborts that whole Album subset.

Application policy is evaluated independently per Album. Another eligible Album selected by the
same query may still be stored, but an unexpected application or store failure stops later Albums.
There is no command-wide rollback. Persistent `Album` has no supported album-level `media` field, so
media remains withheld in partial mode and blocking in strict mode; it is never inferred from or
applied to Items.

Successful application mutates only mapped persistent Album fields and calls
`Album.store(inherit=True)` once. Normal beets behavior propagates inheritable Album fields to Item
database rows. Noqlen does not assign Item metadata or call `Item.store()` itself. Physical file tags
remain unchanged: CLI database application does not call `Item.write()`, tag synchronization, file
moves, or art operations.

All selected Albums are planned before the first database write. Persistence then occurs one Album
at a time using normal beets store transactions. There is no command-wide rollback: if one Album is
stored and a later Album store fails, the earlier database change may remain and later Albums are
not attempted.

During importer enrichment, Noqlen mutates only eligible fields on the selected `AlbumInfo`. It does
not directly mutate Items or persistent Albums, add library records, write tags, or move/copy files.
After selected-release enrichment, normal beets import behavior determines Item application,
database persistence, file handling, and tag writing. Consequently, importer `apply: true` is a real
metadata application feature: the normal import can persist enriched values to the beets library
and, depending on beets configuration, file metadata.

Field Authority expresses provider preference and ordering for each field. Provider Capabilities
describe the fields each current adapter can actually produce. An enabled provider is contacted only
when its capabilities intersect both enabled user fields and its Field Authority entries; authority
may retain future fallback vocabulary that an adapter does not implement yet.

Set `providers.discogs.enabled: true` to preview resolved Discogs decisions after selecting an album
match. A non-empty `NOQLENMETA_DISCOGS_TOKEN` takes precedence over
`providers.discogs.user_token`; direct Discogs release-ID lookups do not require a token. Tokens are
redacted and never included in preview output.

Set `providers.musicbrainz.enabled: true` to enrich releases for which beets already knows an exact
MusicBrainz release MBID. No MusicBrainz credentials are required or stored by Noqlen. The provider
performs one direct release lookup and supports labels, catalog numbers, barcode, release country,
release year, and media format. Release year comes from the selected release date, not the release
group's first release date, so reissues retain edition-specific year semantics. Multiple labels,
catalog numbers, and media formats remain structured; existing singular target mappings may report
mapping blockers rather than discard or join those values.

Set `providers.lastfm.enabled: true` to enrich the selected album identity from Last.fm
`album.getTopTags`. Last.fm top tags are community-generated and are not typed as
genre/style/mood. Noqlen therefore filters tags through beets' packaged LastGenre genre vocabulary
and does not infer styles or moods from arbitrary social tags. Tags below weight 10 are discarded,
and at most the first three accepted genres are proposed as one structured value. There is no
Last.fm credential configuration: Noqlen uses the Last.fm key that current beets explicitly shares
with plugins, without displaying or persisting it.

Under the default genres authority, Discogs is preferred over Last.fm and Last.fm is preferred over
iTunes. Users can reorder those built-in providers through `resolution.authority.genres`; changing
authority does not expand Last.fm beyond its current genres-only capability.

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

The plugin resolves release candidates from Discogs, MusicBrainz, Last.fm, and iTunes through one
shared planning path. During importer preview, LRCLIB can plan lyrics for selected album-match or
singleton tracks through the same Field Authority, resolver, and `ChangePlan`. A read-only
`TrackTargetPlan` then maps plain lyrics to `TrackInfo.lyrics` and exposes synchronized lyrics as a
mapping blocker. Importer release enrichment separately maps its release `ChangePlan` to
`BeetsTargetPlan`; the album-only library command maps only release plans to `LibraryTargetPlan`.
Importer application can mutate selected `AlbumInfo` and losslessly mapped fields on selected
`TrackInfo` through separate guarded strict or partial boundaries. CLI application is separately
authorized by `--apply`, remains strict by default, and permits safe partial database application
only with `--apply --partial`. Items, track database metadata, and files remain outside Noqlen track
application.

See `docs/context/current.md` and `docs/context/handoff.md` before starting a development block.
