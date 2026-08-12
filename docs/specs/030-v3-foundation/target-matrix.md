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
