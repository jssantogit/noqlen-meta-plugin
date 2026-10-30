# V3 Target and Interoperability Matrix

## Audited contract

The package declares `beets>=2.12,<3`. Wave 0A audited beets 2.12.0 and the
MediaFile 0.17.0 minimum required by that beets release. The host interpreter
also contained an inconsistent MediaFile 0.16.0 installation; all baseline
verification used the isolated, coherent 2.12.0/0.17.0 environment.

`TrackInfo` and `AlbumInfo` accept arbitrary mapping keys. That does not make an
arbitrary key a native `Item`, `Album`, or MediaFile persistence contract.
Native below means an explicit beets model field with the appropriate semantic
meaning. Typed flexible fields are justified only for stable musical concepts;
structured provenance/relationships remain internal.

Legend: F/V = FLAC or Ogg Vorbis comments; O = Opus comments; ID3 = MP3; MP4 =
M4A atoms/freeforms. L = lossless for the canonical value; LS = flattened or
lossy; none = no defensible interoperable target.

## Dates and release classification

| Concept | Entity; cardinality; canonical type | Native beets / MediaFile | Format representation | Extra target | Loss/risk and recommendation |
| --- | --- | --- | --- | --- | --- |
| `date/year` | Release; 0..1; partial date `(year, month?, day?)` | `AlbumInfo`, `Album`, inherited `Item`: `year/month/day`; MediaFile `date` | F/V/O `DATE`; ID3 `TDRC`; MP4 `©day` | None; provenance internal | L for partial precision. Use all components, not year alone. ID3 calls TDRC recording time, but beets ecosystem uses it for release date. |
| `originaldate/original_year` | Release lineage; 0..1; partial date | Native `original_year/month/day`; MediaFile original date components | F/V/O `ORIGINALDATE`; ID3 `TDOR`; MP4 freeform convention | None; provenance internal | L in beets/MediaFile; MP4 ecosystem support weaker. Never infer from edition date. |
| `recording_date` | Recording; 0..1 partial date, possibly bounded interval later | None distinct from release date | Existing DATE/TDRC collide with release-date mapping; MP4 none | Typed DB ISO partial-date field; interval needs structured state | DB L, embedded none. Do not alias to date/year. |
| `release_type` | Release Group; 0..1 enum | `albumtype`; MediaFile album type | F/V/O `RELEASETYPE`/MB type; ID3/MP4 MB Album Type conventions | None | L if primary remains first. |
| `release_secondary_types` | Release Group; 0..n normalized set | `albumtypes` combines primary+secondary | Same repeated/list tag | Typed separate multivalue, plus native combined projection | Native projection LS. Preserve semantic split in DB. |
| `release_status` | Release; 0..1 enum | `albumstatus` | F/V/O release status; ID3/MP4 MB Album Status convention | None | L. Use native field. |
| `edition` | Release; 0..1 designation string | None; `albumdisambig` is not equivalent | No stable universal mapping | Typed DB string; provenance/conflicts internal | DB L, file none. Do not collapse format, country, status, remaster or title keywords into edition. |

## Identity, Works, and credits

| Concept | Entity; cardinality; canonical type | Native beets / MediaFile | Format representation | Extra target | Loss/risk and recommendation |
| --- | --- | --- | --- | --- | --- |
| ISRC | Recording; 0..n canonical codes | `Item.isrc` and MediaFile `isrc` are scalar | F/V/O repeated ISRC possible; ID3 `TSRC`; MP4 freeform | Typed plural DB field; optional deterministic scalar projection | L only for 0/1 natively. Never discard additional valid ISRCs internally. |
| ISWC | Work; 0..n canonical codes | None | No audited stable cross-format mapping | Work relationship/internal store; typed query projection only if needed | Do not invent private tags. |
| Work | Recording-to-Work; 0..n structured relationships | Scalar `work`, `work_disambig`, `mb_workid`; MediaFile has MB Work ID and MP4 work title support | F/V/O `WORK`; ID3 ecosystem `WORK`/`TIT1`; MP4 `©wrk`; MB Work ID conventions | Structured relation store for multiplicity | Native scalar L only for one Work. Use scalar compatibility projection when unambiguous. |
| Composer | Work/Recording credit; 0..n records | Native composers/IDs; MediaFile composers | F/V/O `COMPOSER`; ID3 `TCOM`; MP4 `©wrt` | Structured relation state | Names L; role/scope LS. |
| Lyricist | Work/Recording credit; 0..n | Native lyricists/IDs; MediaFile lyricists | F/V/O `LYRICIST`; ID3 `TEXT`; MP4 freeform | Structured relation state | Names L; structure LS. |
| Arranger | Work/Recording credit; 0..n | Native arrangers/IDs; MediaFile arrangers | F/V/O `ARRANGER`; ID3 `TIPL`; MP4 freeform is weaker convention | Structured relation state | Names mostly L; exact scope/role LS. |
| Producer | Recording or Release; 0..n scoped records | None | F/V/O `PRODUCER`; ID3 `TIPL`; MP4 freeform convention | Typed Item and Album name projections plus structured state | Preserve source scope; never inherit release producer to every track. |
| Conductor | Recording/Release; 0..n | None | F/V/O `CONDUCTOR`; ID3 `TPE3`; MP4 freeform | Typed names projection plus structured state | Names mostly L; relation structure LS. |
| Performers/instruments | Recording/Release; 0..n `{artist, role, instrument, scope}` | None | F/V/O performer convention; ID3 `TMCL`; MP4 none | Structured relationship state; optional derived views | Do not delimiter-encode canonical records. MP4 write unsupported. |
| Featured/guest artists | Recording/Release; 0..n role-bearing credits | Native artist lists/credits preserve names and IDs, not explicit roles | Native artist/credit tags | Structured role state; optional query views | Do not rewrite primary artist/albumartist in ordinary enrichment. |
| Structured artist credits | Recording/Release; ordered nodes and joins | Native artists, IDs, credited-name lists and display credit | MediaFile parallel artist/credit lists | Complete canonical structure internal | Parallel lists are useful projection but may lose joins/roles; validate alignment. |

## Titles, language, state, and lyrics

| Concept | Entity; cardinality; canonical type | Native beets / MediaFile | Format representation | Extra target | Loss/risk and recommendation |
| --- | --- | --- | --- | --- | --- |
| Alternate/localized titles | Recording/Release/Work; 0..n `{text, language?, script?, type}` | `TrackInfo.track_alt` is not durable; otherwise none | No universal structured mapping | Internal alias records | Do not JSON/delimiter encode or replace main title automatically. |
| Language | Release main-text language; 0..1 | Native `language`; MediaFile languages | F/V/O `LANGUAGE`; ID3 `TLAN`; MP4 freeform | None for release language | L when scope/code standard is explicit. Not vocal language. |
| Script | Release/main title; 0..1 ISO 15924 | Native `script`; MediaFile script | F/V/O/ID3/MP4 established conventions | None | L for selected main script; alias scripts remain on alias records. |
| Transliteration | Alias representation; 0..n typed records | None | None | Internal alias records | Keep distinct from script and title replacement. |
| `track_version/mix` | Recording/track; 0..1 normalized type plus source description | `subtitle` is a lossy projection; no native structure | F/V/O VERSION/SUBTITLE; ID3 `TIT3`; MP4 convention incomplete | Typed DB representation or two stable fields; evidence internal | Do not infer solely from title keywords. |
| `vocal_languages` | Recording; 0..n language codes | No correct Item field; MediaFile `languages` can carry plural audio language | F/V/O LANGUAGE; ID3 TLAN; MP4 freeform | Typed multivalue DB field | L if V3 explicitly defines file LANGUAGE as vocal/audio language. Do not reuse release/artist language. |
| Instrumental | Recording; tri-state true/false/unknown | None | No audited stable universal mapping | Typed nullable enum/string | DB L, file none. Unknown is not false; require relationship or equivalent evidence. |
| Explicitness | Recording/track; explicit/clean/unknown | None | MP4 advisory atom exists but is not exposed by MediaFile; no universal mapping | Typed enum DB field | DB L, universal file none. Absence is unknown, not clean. |
| Lyrics | Recording; selected plain text plus internal representation metadata | Native `lyrics`; MediaFile lyrics | F/V/O LYRICS; ID3 USLT; MP4 `©lyr` | Internal source/language/variant state | Selected text L; multiple variants flatten. |
| Synced lyrics | Recording; timed representation/LRC | No Item target; MediaFile 0.17 only supports ID3 SYLT | ID3 only; F/V/O/MP4 none | Verified `.lrc` sidecar; optional DB index/state | `.lrc` L and authoritative. Do not degrade to plain lyrics or claim universal embedding. |

## Artwork and audio

| Concept | Entity; cardinality; canonical type | Native beets / MediaFile | Format representation | Extra target | Loss/risk and recommendation |
| --- | --- | --- | --- | --- | --- |
| Front artwork | Release; 0..1 canonical typed asset | Album `artpath`; MediaFile typed images | FLAC picture/Vorbis block/Opus block/ID3 APIC preserve Front; MP4 covr untyped | `cover.jpg` asset | L except type is implicit/lost in MP4. Sidecar authoritative. |
| Back artwork | Release; 0..n typed asset | No second artpath; MediaFile image type Back | FLAC/Vorbis/Opus/ID3 preserve Back; MP4 loses type | `back.jpg` asset | Sidecar authoritative; do not replace unrelated embedded images. |
| Disc artwork | Release Medium; 0..n keyed by disc | MediaFile generic Medium image, no disc index | Typed generic Medium except MP4; no multidisc index | `disc.jpg` or indexed assets plus internal association | Single disc conditional L; multidisc embedding LS. Do not guess CAA disc number. |
| BPM | Recording; 0..1 finite positive float | Native BPM; project uses float DB, MediaFile writes integer | F/V/O BPM; ID3 TBPM; MP4 integer tmpo | Method/version/confidence internal | DB L; file only integral values L. Preserve current fractional write blocker. |
| Key | Recording; 0..1 canonical pitch class+mode | Native `initial_key`; MediaFile initial key | F/V/O INITIALKEY; ID3 TKEY; MP4 freeform | Method/version/confidence internal | L after enharmonic/mode normalization. |
| Energy | Recording; 0..1 documented nullable float | None | No audited interoperable mapping | Typed nullable float DB; method/version internal | DB L, file none. Do not invent a private tag. |
| Danceability | Recording; 0..1 documented nullable float | None | No audited interoperable mapping | Typed nullable float DB; method/version internal | DB L, file none. |
| `energy_level` | Recording; deterministic enum derived from Energy | None | No file target needed | Prefer computed plugin field; persist only for query need | Recalculable, not provider evidence. |
| `danceability_level` | Recording; deterministic enum | None | No file target needed | Prefer computed field | Recalculable. |
| `tempo_range` | Recording; deterministic BPM bucket | None | No file target needed | Prefer computed field | Recalculable. |

## Format conclusions

- **FLAC/Vorbis and Opus:** strongest flat multivalue support and typed artwork,
  but cannot preserve arbitrary relationship records. `DATE` semantics conflict
  between Xiph recording-date wording and beets release-date convention.
- **MP3/ID3:** strongest standard frames for credits, ISRC, BPM, key, typed
  artwork and, with MediaFile 0.17, synchronized lyrics. ID3v2.3 can flatten
  multivalues and must be tested separately from v2.4.
- **MP4/M4A:** useful native atoms plus ecosystem freeforms, but artwork is
  untyped, BPM is integer, synced lyrics are absent, and structured performer
  support is weak. A MediaFile self-round-trip alone does not prove external
  interoperability.
- Existing `NOQLEN_*` V2 tags are compatibility behavior, not precedent for new
  private V3 tags. Do not add more merely to mark a format supported.

## Target gaps that block Wave 1+

1. No canonical structured representation for partial dates, tri-state values,
   scoped credits, aliases, Work relationships, or typed assets.
2. Native scalar ISRC/Work targets cannot preserve V3 multiplicity.
3. Synchronized lyrics require `.lrc`; Back/disc artwork require separate asset
   plans and non-destructive embedded-image handling.
4. Recording date, edition, explicitness, Energy and Danceability have safe DB
   targets but no universal embedded representation.
5. Supported beets range should be verified against 2.12 and latest 2.x in CI;
   Wave 0A only established the concrete 2.12.0 contract.

Primary technical references:
[beets 2.12 hooks](https://github.com/beetbox/beets/blob/v2.12.0/beets/autotag/hooks.py),
[MediaFile 0.17](https://github.com/beetbox/mediafile/tree/v0.17.0/mediafile),
[Picard tag mapping](https://github.com/metabrainz/picard-docs/blob/master/appendices/tag_mapping.rst),
[Vorbis comments](https://xiph.org/vorbis/doc/v-comment.html),
[Mutagen ID3](https://mutagen.readthedocs.io/en/latest/api/id3_frames.html), and
[Mutagen MP4](https://mutagen.readthedocs.io/en/latest/api/mp4.html).


## Instrumental V3 implementation — 2026-10-29

The executable V3 `instrumental` field is a **nullable Boolean Item value**.
Only an explicit positive assertion may be proposed; no evidence means
**unknown**, never `false`. An existing explicit `false` is preserved and
conflicting positive evidence produces REVIEW.

MusicBrainz is primary only when the canonical Recording-to-Work `performance`
relationship explicitly includes the `instrumental` attribute. Non-performance
edges, missing attributes, free-text genres/titles and unrelated Work metadata
do not prove instrumental state.

LRCLIB is secondary and may assert `true` only after its existing exact
artist/title/album/duration validation and explicit `instrumental: true`.
Its explicit `false` is deliberately not accepted as proof of vocals. The V2
`get_candidates()` lyrics behavior and request/cache scope are unchanged;
the same normalized response supplies the separate V3 evidence.

The V2 public configuration defaults, provider spec capability sets and
`TRACK_FIELD_TARGETS` remain unchanged. The separate V3 authority capability
registry and track mapper support `fields.instrumental: true` as an explicit
opt-in in development configuration. Application is database-only through the
normal ChangePlan/preview/review/SQLite rollback pipeline. No media-file tag is
advertised or written for instrumental state.


## Explicitness V3 implementation — 2026-10-29

The V3 recording-level `explicitness` field uses **three states**:
`explicit`, `clean`, or **unknown** (no known canonical value).
The executable value is a typed nullable string in the beets Item database;
no universal media-file advisory tag is written. Conflicting existing values
are preserved and require REVIEW before any application.

iTunes supplies track-level evidence only from an unambiguous song in a
bounded storefront search using exact normalized artist, title, album,
track/disc numbers when available, and duration within two seconds.
Existing iTunes track/collection identifiers, when present, must also agree;
different known identities never share a cached verdict. A matching
collection/album cannot assert track explicitness. Search results with two
distinct plausible tracks are deliberately withheld. Provider/network
failure cannot fabricate metadata or block unrelated provider evidence.

The iTunes Search API documents approximately 20 calls/minute. The adapter
serializes searches and spaces request starts by at least 3.1 seconds,
including after failures, while reusing successful/no-data cache entries
for identical exact contexts. This rate-limit cost is opt-in.

The Apple Music/iTunes API documents `trackExplicitness` as
`explicit`, `cleaned`, or `notExplicit`
(https://performance-partners.apple.com/search-api).
V3 maps only **`explicit` → `explicit`** and
**`cleaned` → `clean`**. It treats `notExplicit`, missing,
malformed, and unknown flags as **unknown** rather than proof of a
specifically clean/censored edition. Album-level `collectionExplicitness`
is intentionally ignored.

The V2 iTunes release provider and its public `ProviderSpec` are unchanged.
The separate V3 recording capability and target registries support this
feature as an explicit development opt-in via `fields.explicitness: true`
plus `providers.itunes.enabled: true`. The current CLI remains preview-first,
with explicit database application and unchanged file-write restrictions.


## Vocal languages V3 implementation — 2026-10-29

The opt-in `fields.vocal_languages: true` field is a **Recording-level,
ISO-639-3 multivalue assertion**, distinct from V2 `lyrics_languages`
(Work lyric languages), `artist_languages` and release-title language.
The field is stored as a typed multivalue beets Item field, and no speculative
embedded LANGUAGE tag is written. V2 public config defaults, provider specs,
target registry and legacy Work-language lookup breadth remain frozen.

MusicBrainz Work lyric languages can provide **structurally derived evidence**
for a recording only when the Recording has exactly one validated
`performance` relationship, the Work lookup identity is verified, and that
Work supplies one or more concrete 3-letter language codes. Ambiguous
non-performance or multiple-Work links yield no vocal assertion. Relationship
attributes `instrumental`, `karaoke`, `partial`, `medley`, and `translated`
suppress derivation because the Work's lyrics may not match that audio.
Work attributes `instrumental` or `no lyrics` and generic `zxx`, `mul`,
`und` language values cannot create vocal languages. Duplicate Work links
must retain the union of flags rather than losing a disqualifying attribute.
The exact supporting Work MBID, provenance and source URL are retained.

The resolver preserves existing codes: identical or subset source evidence
KEEPS the local value; an unambiguous superset may PROPOSE; incomparable
sets require REVIEW instead of deleting local languages. An explicit
instrumental assertion from another authoritative provider (or an existing
instrumental=true Item) blocks automatic vocal-language application and
routes the candidate to REVIEW.

This is **not audio-derived language identification**. Even a unique Work
language describes the composition's lyrical language, not guaranteed audio
content, so the feature deliberately has narrow coverage and remains opt-in.
No lyric-language detector or artist-country shortcut is used.

Reference: [MusicBrainz Work language semantics](https://musicbrainz.org/doc/Work)
and [Recording-to-Work Performance relation](https://musicbrainz.org/relationship/a3005666-a872-32c3-ad06-98af558e99b0).


## V3 lossless synchronized lyrics and Back artwork — 2026-10-29

### Exact-track synchronized lyrics

The existing LRCLIB candidate `synced_lyrics` is not treated as a normal
TrackInfo or media-file field: an approved candidate is now routed to a
dedicated **`<audio-stem>.lrc` associated sidecar plan** in the library
`beet nm` command. The V2 TrackInfo mapper, legacy import behavior and
public field defaults are unchanged. A valid timestamped LRC (minimum one
`[mm:ss.xx]` or equivalent time tag) is required. The selected text is
written as UTF-8 without flattening into plain lyrics.

Preview does not write. `--apply` may create the sidecar without
`--write`; the audio file is never rewritten for LRC. An existing
byte-identical sidecar is KEEP, an existing different or non-regular
destination is REVIEW, and invalid/untimed content is BLOCKED.
Application re-reads the Item path from the library and uses a staged,
fsynced file and **atomic no-clobber hardlink**; stale, moved or
concurrently-created destinations are never overwritten. The operation
is a separately verified asset commit, not an audio-tag change.

### Exact-edition Back artwork

A separate V3 `fields.back_artwork: true` opt-in selects one approved
`back: true` image from **exact MusicBrainz Release** CAA metadata;
release-group fallback and multiple approved Back candidates are withheld.
Only trusted CAA HTTPS URLs are admitted. The selected JPEG is downloaded
only on `--apply` and saved as `back.jpg` in the release's item
directories, with no replacement of existing sidecars, no Album.artpath
mutation, and no implicit embed or Front artwork overwrite. It
preserves earlier commits if a later disc-directory target changes,
reporting a partial outcome rather than claiming rollback.

Example user configuration for these **opt-in** development features:

```yaml
noqlenmeta:
  fields:
    synced_lyrics: true
    back_artwork: true
  providers:
    lrclib:
      enabled: true
    coverartarchive:
      enabled: true
```

`beet nm --all` previews and `beet nm --apply --all` applies.
All other identity, field, edition and conflict guards remain active;
this is not yet a V3 release or an authorization to merge.


## V3 structured Recording titles — 2026-10-29

The V3 `fields.alternate_titles: true` opt-in collects **actual
MusicBrainz Recording aliases**, when an exact MBID is already known.
Alternatively, `fields.transliterations: true` alone selects only aliases
explicitly typed `Transliteration` by MusicBrainz, retaining their
recorded locale/script. It does not infer romanization from names or
script similarity, and uses the same non-lossy storage table.
It requests `aliases` from the Recording resource, not by searching for
matching titles or following Work/Release relationships. Alias rows retain
the original text, source Recording MBID, provider, locale, explicit
alias type, optional sort name, primary flag and script subtag when
explicitly encoded in a locale such as `ja-Latn`.

The implementation deliberately excludes aliases identical to the main
Recording title and MusicBrainz `Search hint` aliases. It never changes
Item.title, auto-repairs identity, writes freeform native tags, or flattens
the locale/type metadata into a delimiter-separated string.

Approved rows are persisted in the plugin-owned, append-only
`noqlenmeta_title_alias` table, scoped by Item ID and canonical Recording
MBID. Duplicate rows are idempotent, existing aliases are preserved,
and application verifies a fresh Item path, recording identity, native
title and prior alias snapshot. Preview and read do not create the table;
`--apply` commits only genuinely new rows. Existing V2 public defaults
and exposed generic field/target registries stay frozen. This scope
covers the library `beet nm` command; importer completion, non-Recording
aliases and typed track-version semantics remain separate work.


## Explicit track-version V3 implementation — 2026-10-29

The opt-in `fields.track_version: true` does **not** parse keywords
from the track title or assume a remix/remaster based on title punctuation.
It may propose a version only when the **exact MusicBrainz Recording**
supplies a dedicated `disambiguation` string matching one of a small,
explicitly enumerated whole-string descriptions, e.g. `radio edit`,
`extended mix`, `instrumental version`, `live version`,
`demo version`, `acoustic version`, `album version`,
`single version`, or `remix`. Other comments, including arbitrary
mixed prose, remain unknown. This intentionally underfills rather than
misclassifies.

The proposed version has a normalized type and the original description.
It uses two separately typed beets Item DB fields,
`track_version_type` and `track_version_description`; no speculative
audio-file `VERSION` tag or lossy `subtitle` projection is written.
Existing agreeing state is KEEP; contradicting or partially present
values require REVIEW. Application rechecks exact Recording MBID, Item path,
display title and both previous values, using the same explicit SQLite
SAVEPOINT-backed database mutation pattern as other V3 fields.
Importer-side version projection and richer relationship-typed mix/version
semantics remain open.



## Conservative local Key V3 — implementation 2026-10-29

The V3 library command can opt into local key estimation with two explicit
switches, without modifying V2 public defaults:

```yaml
noqlenmeta:
  fields:
    key: true
  local_analysis:
    key:
      enabled: true
      analysis_mode: window  # full or window
      window_seconds: 90
```

The optional `[audio]` Librosa backend computes a pitch-class distribution and
correlates it against 24 major/minor templates. The policy abstains unless the
leading correlation is >= 0.70 and at least 0.10 above the runner-up. This is
conservative evidence, **not** ground-truth key recognition: modal ambiguity,
modulation, atonal content, percussion, silence and poor harmonic separation
can yield no assertion. The canonical beets notation (`C` major, `Am` minor, etc.) maps to native
`initial_key` and the interoperable `INITIALKEY` file tag. Existing keys are
always preserved; only verified missing values may be proposed. Analysis is available on library preview/apply and on the selected importer
track path, after matching (never as matching/identity evidence). Importer
preview is side-effect-free; opt-in application updates the selected TrackInfo
only, with beets remaining responsible for the subsequent import lifecycle.
The audio backend is loaded lazily and the default remains disabled.


## V3 Energy and Danceability: versioned, opt-in local proxy indices (2026-10-30)

**Semantics and limitations:** These values are *not* Spotify, Echo Nest, or
validated perceptual feature scores. They are two explicitly labeled signal
analysis proxies on a fixed 0..1 scale. They are only comparable when the
methodology and decoder assumptions match, and must not be shown as generic
ground-truth danceability or emotional energy.

- `energy` uses median frame-wise root-mean-square signal amplitude of the
  decoded, full-scale float audio. The `rms-dbfs-v1` transform maps a measured
  level in [-50, -8] dBFS linearly to [0,1] and clamps extremes. It is an
  *amplitude intensity proxy*, not loudness normalization or a model of musical
  activity. Silence and invalid/out-of-range measurements abstain.
- `danceability` uses estimated beat times and spectral onset-strength peaks
  from Librosa. `beat-onset-regularity-v1` requires at least nine strictly
  ordered beats, plausible intervals, inter-beat coefficient of variation
  <= 0.15, and on-beat onset prominence >= 1.25x mean strength. A fixed,
  documented combination of regularity (65%) and prominence (35%) yields a
  *rhythm-stability proxy*, not a validated prediction of suitability to dance.
  Instrumental silence, missing beats, unstable rhythm and weak supporting
  onsets produce unknown instead of 0. The score deliberately excludes BPM.
- `energy_method` and `danceability_method` are separate typed DB strings.
  Values are nullable floats; missing is unknown, not 0. Each method identifier
  is recorded alongside any new score and is not silently relabeled on conflict.
  All four fields are Item/TrackInfo DB-only: **no new embedded media tags**.
- Pure computed, nonpersisted `score_level` (low <=.33, medium <=.67, high)
  and `tempo_range` (slow <90, medium <140, fast) helpers are optional
  presentation buckets, not independent provider evidence.

Enable *both* the specific fields and the local backend; defaults remain frozen:

```yaml
noqlenmeta:
  fields:
    energy: true
    danceability: true
  local_analysis:
    audio_features:
      enabled: true
      analysis_mode: window   # full or centered window
      window_seconds: 90
```

Only a missing field is eligible. Analysis runs once for all requested missing
features of an eligible track, with optional Librosa imported lazily.
Library CLI preview does not write; `--apply` stores to the beets DB.
The importer may enrich only the already selected TrackInfo, after matching,
and does not use this evidence for identity selection. `--write` never embeds
these DB-only values.

Reference algorithm definitions: [Librosa RMS](https://librosa.org/doc/latest/generated/librosa.feature.rms.html),
[Librosa onset strength](https://librosa.org/doc/latest/generated/librosa.onset.onset_strength.html),
[Librosa beat tracking](https://librosa.org/doc/latest/generated/librosa.beat.beat_track.html).
Thresholds are product-specific heuristics, not independently calibrated
classification thresholds. Human-labeled evaluation on diverse real audio is
still required before claiming perceptual validity.
