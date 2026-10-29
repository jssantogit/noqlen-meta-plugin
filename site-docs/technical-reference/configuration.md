# Configuration Reference

You will find every public Noqlen Meta YAML key, its default, users, effects,
and write authority. The canonical complete example is
[`full-config.yaml`](../examples/full-config.yaml).

All paths below are relative to the beets configuration root and begin with
`noqlenmeta`.

## Importer Controls

### `noqlenmeta.preview`

- Type: boolean. Default: `true`. Accepted: `true`, `false`.
- Used by: importer ordinary release and selected-track enrichment only.
- Effect: renders importer ordinary plans when work is eligible.
- Grants writes: no.
- Interaction: independent of `noqlenmeta.apply`; neither setting controls the library command.
- Example: `preview: true`.

### `noqlenmeta.apply`

- Type: boolean. Default: `false`. Accepted: `true`, `false`.
- Used by: importer ordinary release and selected-track enrichment only.
- Effect: permits guarded mutation of metadata already selected by beets.
- Grants writes: selected importer metadata only; not direct database or file writes.
- Interaction: final persistence and tag writing remain normal beets importer behavior.
- Example: `apply: true`.

### `noqlenmeta.apply_mode`

- Type: string. Default: `strict`. Accepted: `strict`, `partial`.
- Used by: importer ordinary enrichment only.
- Effect: classifies selected release/track ordinary metadata application.
- Grants writes: no; `noqlenmeta.apply: true` is still required.
- Does not affect: `beet nm --apply`, identity, or identity-tag modes.
- Example: `apply_mode: partial`.

The value is normalized for surrounding whitespace and case when importer
application is enabled. Invalid values stop application.

## Importer Identity Controls

| Path | Type | Default | Used by | Effect and interaction |
| --- | --- | --- | --- | --- |
| `noqlenmeta.identity.enabled` | boolean | `false` | Identity importer | Master gate for identity audit; separate from enrichment provider settings. |
| `noqlenmeta.identity.preview` | boolean | `true` | Identity importer | Renders identity audit when enabled; grants no writes. |
| `noqlenmeta.identity.apply` | boolean | `false` | Identity importer | Permits coherent selected-metadata repair; requires `identity.enabled: true`. |

Accepted values are `true` or `false`. These keys do not control the library
`--identity` command. Identity importer repair mutates selected `AlbumInfo` and
`TrackInfo` only; beets owns later persistence and file behavior.

`providers.musicbrainz.enabled` neither enables nor disables identity audit.

```yaml
identity:
  enabled: true
  preview: true
  apply: false
```

## AcoustID Controls

AcoustID is recording-identity evidence for existing-library workflows. It is
not an importer metadata provider. All settings are validated before target,
backend, credential, or network work.

| Path | Type | Default | Effect |
| --- | --- | --- | --- |
| `noqlenmeta.acoustid.enabled` | boolean | `false` | Enables optional AcoustID evidence in `--identity`; standalone `--acoustid` is explicit authority. |
| `noqlenmeta.acoustid.reuse_existing` | boolean | `true` | Reuses a valid stored fingerprint; a stored AcoustID ID is not fresh evidence. |
| `noqlenmeta.acoustid.compute_missing` | boolean | `false` | Permits standalone missing-fingerprint calculation; never permits it in `--identity`. |
| `noqlenmeta.acoustid.lookup` | boolean | `true` | Permits lookup when valid fingerprint material exists. |
| `noqlenmeta.acoustid.use_for_identity` | boolean | `true` | Allows decisive evidence to filter MusicBrainz candidates when AcoustID is enabled. |
| `noqlenmeta.acoustid.min_score` | finite number | `0.90` | Inclusive AcoustID result threshold from `0.0` through `1.0`. |
| `noqlenmeta.acoustid.min_margin` | finite number | `0.05` | Inclusive unique-recording margin from `0.0` through `1.0`. |
| `noqlenmeta.acoustid.max_results` | integer | `5` | Retains from `1` through `20` result groups. |
| `noqlenmeta.acoustid.max_recordings_per_result` | integer | `10` | Retains from `1` through `50` recording MBIDs per result. |
| `noqlenmeta.acoustid.timeout_seconds` | finite number | `15.0` | Backend/request timeout from `1.0` through `60.0` seconds. |
| `noqlenmeta.acoustid.requests_per_second` | finite number | `3.0` | Positive process-local ceiling, at most `3.0`. |
| `noqlenmeta.acoustid.cache_entries` | integer | `256` | Process-local lookup cache size from `0` through `4096`. |
| `noqlenmeta.acoustid.fpcalc` | non-empty string | `fpcalc` | Executable used only for authorized calculation. |

The AcoustID client key is available exclusively through
`NOQLENMETA_ACOUSTID_API_KEY`; there is no credential setting in YAML.

## Field Controls

Every field key is boolean, accepts `true` or `false`, grants no write
permission, and is used only where a provider scope and lossless target mapping
exist. Enabling a field does not guarantee an enabled provider can supply it.

| Path | Default | Importer use | Ordinary library use | Important interaction |
| --- | ---: | --- | --- | --- |
| `noqlenmeta.fields.genres` | `true` | Release | Album | MusicBrainz, Discogs, Last.fm, iTunes; list mapping. |
| `noqlenmeta.fields.styles` | `true` | Release | Album | Discogs structured styles plus classified MusicBrainz/Last.fm semantic tags; typed plural storage is lossless and legacy `style` is a read fallback. |
| `noqlenmeta.fields.labels` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block singular targets. |
| `noqlenmeta.fields.catalog_numbers` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block. |
| `noqlenmeta.fields.barcodes` | `true` | Release | Album | Discogs/MusicBrainz; multiple values can block. |
| `noqlenmeta.fields.country` | `true` | Release | Album | Discogs/MusicBrainz; iTunes storefront is not release country. |
| `noqlenmeta.fields.date` | `true` | Release | Album | Exact edition date; supplies native date components and suppresses legacy year competition. |
| `noqlenmeta.fields.original_date` | `true` | Release Group | Album | First Release Group date, distinct from edition and recording dates. |
| `noqlenmeta.fields.release_type` | `true` | Release Group | Album | Controlled primary type. |
| `noqlenmeta.fields.release_secondary_types` | `true` | Release Group | Album | Separate typed plural secondary types. |
| `noqlenmeta.fields.release_status` | `true` | Release | Album | Controlled MusicBrainz release status. |
| `noqlenmeta.fields.edition` | `true` | Release | Album | Controlled Discogs edition designation; database only. |
| `noqlenmeta.fields.year` | `true` | Release | Album | MusicBrainz, Discogs, iTunes. |
| `noqlenmeta.fields.media` | `true` | Release | Preview/block | Importer target exists; persistent Album target does not. |
| `noqlenmeta.fields.format_descriptions` | `true` | Preview/block | Preview/block | Discogs can supply it; there is currently no lossless ordinary target. |
| `noqlenmeta.fields.moods` | `true` | Typed track target | Typed Item target | Classified MusicBrainz tags; optional Last.fm corroboration/fallback. |
| `noqlenmeta.fields.bpm` | `true` | Numeric track target | Float Item target | Enables preservation/sync and optional local Librosa analysis. |
| `noqlenmeta.fields.lyrics_languages` | `true` | Typed track target | Typed Item target | Exact Recording -> Work lookup; stores three-letter codes. |
| `noqlenmeta.fields.artist_countries` | `true` | Typed release/track targets | Typed Album/Item targets | Structurally derived MusicBrainz geographic identification. |
| `noqlenmeta.fields.artist_areas` | `false` | Typed release/track targets | Typed Album/Item targets | Trustworthy MusicBrainz main area; no string inference. |
| `noqlenmeta.fields.artist_languages` | `true` | Typed release/track targets | Typed Album/Item targets | Three-letter codes derived only from current-target Works. |
| `noqlenmeta.fields.lyrics` | `false` | Selected tracks | Items | LRCLIB plain lyrics use shared import/library resolution. |
| `noqlenmeta.fields.synced_lyrics` | `false` | Preview/block | Preview/block | No lossless synchronized-lyrics target is delivered. |
| `noqlenmeta.fields.cover` | `true` | Album artwork | Album artwork | Exact CAA front selection and deterministic `cover.jpg`. |
| `noqlenmeta.fields.isrcs` | `true` | Recording | Item | All exact ISRCs; scalar native/file projection only when singular. |
| `noqlenmeta.fields.works` | `true` | Recording | Item | Structured exact Work relationships; plural Work IDs persist in the database. |
| `noqlenmeta.fields.iswcs` | `true` | Work | Item | Work-scoped plural ISWCs; database only. |
| `noqlenmeta.fields.recording_date` | `true` | Recording | Item | Structurally proven date; canonical partial-date database text only. |
| `noqlenmeta.fields.composers` | `true` | Work credits | Item | Native plural names/IDs plus structured state; generic writer is not promoted. |
| `noqlenmeta.fields.lyricists` | `true` | Work credits | Item | Native plural names/IDs plus structured state. |
| `noqlenmeta.fields.producers` | `true` | Recording/Release credits | Item/Album | Scope is preserved; database-only structured relation. |
| `noqlenmeta.fields.arrangers` | `true` | Work/Recording credits | Item | Native plural names/IDs plus structured state. |
| `noqlenmeta.fields.conductors` | `true` | Recording/Release credits | Item/Album | Scope is preserved; database-only structured relation. |
| `noqlenmeta.fields.performers` | `true` | Recording/Release credits | Item/Album | Instruments remain in structured state rather than encoded text. |
| `noqlenmeta.fields.featured_artists` | `true` | Explicit featured/guest credits | Item/Album | Does not rewrite primary artist fields. |
| `noqlenmeta.fields.structured_artist_credits` | `true` | Ordered MusicBrainz credits | Item/Album | Preserves credited names, MBIDs, order, and join phrases. |

Example:

```yaml
fields:
  genres: true
  lyrics: false
```

Field settings do not control identity importer, identity library, or
identity-tag commands, whose four fields are fixed.

## Genre Classification

`noqlenmeta.fields.genres` remains the enable/disable switch for the field.
The separate settings below tune classification only; they do not enable a
provider or grant write authority.

### `noqlenmeta.genres.num_genres`

- Type: integer. Default: `1`. Accepted range: `1` through `10`.
- Effect: limits the number of independently evidenced resolved genres.
- Interaction: the default favors one specific trustworthy result. Higher
  values do not add broad parents implicitly.

### `noqlenmeta.genres.promote_styles`

- Type: boolean. Default: `true`. Accepted: `true`, `false`.
- Effect: allows a Discogs style recognized by the packaged Noqlen taxonomy to
  participate in genre classification.
- Interaction: a promoted value remains independently present in `styles`.

Noqlen Meta packages its own MusicBrainz-derived genre taxonomy and does not
require the LastGenre plugin. Classification does not download taxonomy data
during ordinary execution.

```yaml
genres:
  num_genres: 1
  promote_styles: true
```

### `noqlenmeta.moods.max_moods`

- Type: integer. Default: `1`. Accepted range: `1` through `10`.
- Effect: bounds independently evidenced canonical moods without padding.

```yaml
moods:
  max_moods: 1
```

## Provider Controls

Every `enabled` key is boolean, accepts `true`/`false`, and grants no write
permission. Release providers are used by importer release
enrichment and ordinary library mode. LRCLIB is used only for selected importer
tracks and existing-library Items. No provider key controls identity-tag mode.

| Path | Type | Default | Effect and dependencies |
| --- | --- | --- | --- |
| `noqlenmeta.providers.discogs.enabled` | boolean | `false` | Enables release collection when field authority intersects Discogs capability; search needs the optional Discogs dependency. |
| `noqlenmeta.providers.discogs.user_token` | string | empty | Optional Discogs token; redacted; a non-empty `NOQLENMETA_DISCOGS_TOKEN` environment value takes precedence. |
| `noqlenmeta.providers.musicbrainz.enabled` | boolean | `true` | Zero-credential exact-MBID Release/Recording/Work/Artist semantic backbone; no fuzzy search; does not control identity audit. |
| `noqlenmeta.providers.lastfm.enabled` | boolean | `false` | Enables classified Track -> Release -> Artist fallback for unresolved genres/styles/moods; uses beets' shared API key. |
| `noqlenmeta.providers.itunes.enabled` | boolean | `false` | Enables album genres/year from the public search API. |
| `noqlenmeta.providers.itunes.storefront` | string | `us` | Two ASCII letters such as `us`, `gb`, or `jp`; normalized lowercase when iTunes is used. |
| `noqlenmeta.providers.lrclib.enabled` | boolean | `false` | Enables exact-signature selected-track lookup; no API key. |
| `noqlenmeta.providers.coverartarchive.enabled` | boolean | `true` | Enables exact Release artwork metadata, then Release Group fallback only after definitive absence; no API key. |

## Artwork And BPM

- `noqlenmeta.artwork.size`: `original`, `1200`, `500`, or `250`; default `original`. Explicit thumbnail sizes are maxima and never escalate. A non-JPEG original uses CAA JPEG thumbnails in `1200 -> 500 -> 250` order.
- `noqlenmeta.artwork.replace_existing`: boolean, default `false`. Existing `cover.jpg` or any embedded image preserves the album as curated. With replacement enabled, one selected CAA front becomes uniform across discs and tracks.
- `noqlenmeta.bpm.round`: boolean, default `false`; rounding happens before persistence.
- `noqlenmeta.bpm.recalculate_existing`: boolean, default `false`; existing BPM otherwise avoids analysis.
- `noqlenmeta.bpm.octave_normalization`: boolean, default `false`; only powers of two may move BPM into the configured range.
- `noqlenmeta.bpm.octave_range.min`: positive finite number, default `70`.
- `noqlenmeta.bpm.octave_range.max`: positive finite number greater than `min`, default `180`.
- `noqlenmeta.local_analysis.bpm.enabled`: boolean, default `false`.
- `noqlenmeta.local_analysis.bpm.analysis_mode`: `full` or `window`; default `full`.
- `noqlenmeta.local_analysis.bpm.window_seconds`: positive finite number, default `90`; window mode uses one centered window.
- `noqlenmeta.local_analysis.mood.enabled`: boolean, default `false`.

Install `beets-noqlenmeta[audio]` to enable the lazy Librosa backend. Local BPM
failure is isolated to that track. There is no external BPM provider and no
local mood model. `--write` never starts analysis or changes prepared evidence.

Artwork is album-only. CAA accepts only `front: true` plus `approved: true`.
Sidecars are always named `cover.jpg`; multidisc albums receive identical bytes
in every real disc directory. `--apply` writes and verifies sidecars and
`Album.artpath`; `--apply --write` additionally embeds the same bytes.

Discogs remains opt-in and its structured ordered `styles` tuple takes
precedence over community style tags. MusicBrainz and Last.fm community tags
are persisted only after deterministic classification; unknown tags are not
accepted. Semantic file synchronization uses custom lossless list descriptors
for `styles`, `moods`, `lyrics_languages`, `artist_languages`,
`artist_countries`, and `artist_areas`.

Token example without a secret value:

```yaml
providers:
  discogs:
    enabled: true
    user_token: ""
```

Prefer setting `NOQLENMETA_DISCOGS_TOKEN` in the process environment. Never
commit a real token. Direct Discogs release-ID lookup does not require a token;
search generally does.

## Resolution Controls

These three mapping settings are used by importer ordinary enrichment and the
ordinary library command. They are not used by either identity mode and grant
no write permission.

### `noqlenmeta.resolution.authority`

- Type: mapping from field name to a non-empty ordered list of current provider names.
- Default: `{}` (all fields use built-in authority).
- Accepted providers: `discogs`, `musicbrainz`, `lastfm`, `itunes`, `lrclib`.
- Effect: replaces the built-in provider order for each named field.
- Validation: field/provider names must be known and unique after normalization.
- Interaction: does not enable providers or add capabilities.

```yaml
authority:
  genres: [musicbrainz, discogs, lastfm, itunes]
```

### `noqlenmeta.resolution.min_confidence`

- Type: mapping from field name to finite number.
- Default: `{}`; built-in threshold is `0.8` for each field.
- Accepted range: inclusive `0.0` through `1.0`; booleans are invalid.
- Effect: candidates below the field threshold are ineligible.
- Grants writes: no.

```yaml
min_confidence:
  genres: 0.85
```

### `noqlenmeta.resolution.preserve_existing`

- Type: mapping from field name to boolean.
- Default: `{}`; built-in behavior is `true` for each field.
- Accepted: `true`, `false`.
- Effect: when false, a qualified candidate may replace a conflicting current value without `REVIEW`.
- Grants writes: no; importer still needs `apply: true`, and the library command still needs `--apply`.

```yaml
preserve_existing:
  year: false
```

## Complete Examples

- [`minimal-config.yaml`](../examples/minimal-config.yaml) is the safe starting point.
- [`full-config.yaml`](../examples/full-config.yaml) contains every public key exactly once with valid values.

The full example is illustrative, not a recommendation to enable every
provider or field. AcoustID has no audio-file write authority. Ordinary file
replacement requires `--apply --write`; legacy `--identity-tags --write`
authority remains unchanged.
