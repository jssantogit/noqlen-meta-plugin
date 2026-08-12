# V2 to V3 Migration Audit

## Compatibility rule

V3 is evolutionary. A valid V2 configuration and library continue to work when
the same semantics remain safe. New fields begin absent. Migration preference
is compatible alias, then in-memory migration with a clear warning, and only
then rejection when preserving old behavior would be semantically dangerous.
No config reset or library reimport is proposed.

## Classification

| V2 surface | V3 status | Migration recommendation |
| --- | --- | --- |
| `genres` | Same canonical taxonomic field and specialized resolver | Keep name, typed list, configuration and current evidence. New providers/scopes must not bypass taxonomy. |
| `styles` and legacy scalar `style` read fallback | Same canonical multivalue field | Keep `styles`; retain `style` as read-only compatibility alias where current behavior already does so. Do not rewrite plural to scalar. |
| `moods` | Same canonical controlled multivalue field | Keep existing values/config. Future audio Energy is not mood and must not replace it. |
| labels, catalog numbers, barcodes, country, media, format descriptions | Same release/catalog concepts | Preserve names and V2 authority behavior unless the V3 matrix explicitly narrows an unsafe source. Existing multiplicity blockers remain until safe targets exist. |
| `year` | Same field name but richer date model around it | Keep as edition year projection. Populate from accepted `date`, never original or recording date. Existing year is reusable. |
| `lyrics` | Same selected plain-lyrics representation | Keep native Item/MediaFile field and existing content. V3 conflict/superiority rules are conservative; no automatic overwrite. |
| `synced_lyrics` | Same canonical concept, previously blocked for normal target | Keep key/config valid. Add `.lrc` target later; do not flatten into `lyrics`. |
| `cover` field switch | Same user intent for primary Front artwork, but V3 has typed assets | Keep `fields.cover` as an alias enabling Front. Do not rename existing file automatically. Add Back/disc controls only when public design requires them. |
| `cover.jpg` and Album `artpath` | Existing Front asset | Reuse as Front. Verify before replacement. It does not prove Back/disc absence. |
| `bpm` | Same musical concept, future resolver/methodology richer | Preserve valid value. Record method/version as unknown/legacy when provenance is unavailable; do not recompute merely for migration. |
| `lyrics_languages` | Semantics change: currently Work lyric-language evidence; V3 canonical field is sung/vocal language | Keep persisted V2 field and config as legacy lyric-language evidence. Do not automatically rename values to `vocal_languages`. |
| `artist_languages` | Contextual V2 aggregate, not vocal language | Keep unchanged as legacy/contextual semantic field if V3 retains it outside core. Never merge into vocal languages. |
| `artist_countries`, `artist_areas` | Same contextual artist geography | Keep values and config. They do not imply release country or vocal language. |
| Four MusicBrainz IDs | Same identity contract | Preserve exactly and retain explicit conservative repair. New ISRC/Work fields cannot alter their authority. |
| `acoustid_id`, `acoustid_fingerprint`, AcoustID config | Same isolated identity-evidence subsystem | Preserve values/config and frozen boundary. Never migrate into ordinary provider authority or direct MBID write. |
| Provider enablement/storefront/token settings | Same V2 providers and defaults | Preserve all valid keys. New capabilities remain gated and cannot cause new calls solely because an old provider is enabled unless the corresponding V3 field is enabled. |
| `resolution.authority`, `min_confidence`, `preserve_existing` | Valid V2 field-policy overrides | Preserve for unchanged fields. Translate ordered authority to explicit primary/secondary/fallback semantics only where behavior is equivalent; warn/reject ambiguous new-role mappings rather than guess. |
| Preview/apply/write, strict/partial | Same safety semantics | Preserve unchanged. V3 sidecars/assets still require verified plans and stale-state checks. |

## New V3 concepts

These begin absent and do not require reconstruction:

- full current partial date and original partial date;
- recording date;
- primary and secondary release classification and release status;
- edition;
- plural ISRC, Work/ISWC;
- producer, conductor, structured performer/instrument and scoped credits;
- structured featured/guest and artist credits;
- alternate/localized title records, script and transliteration;
- track version/mix;
- `vocal_languages`;
- instrumental and explicitness tri-state;
- Back/disc artwork;
- Key, Energy, Danceability and derived buckets;
- internal provenance, method/version, rejected evidence and diagnostics.

Where beets already has a native value, V3 may import it as existing current
state. Lack of V3 provenance means origin unknown, not invalid.

## Fields with expanded semantics

### `year`, `date`, and original date

- Existing V2 `year` means the specific selected edition year and remains valid.
- V3 adds month/day precision without converting a year to January 1.
- `original_year` and `originaldate` are separate. Never rename `year` to
  `original_year`, copy one into the other, or let beets' `original_date` display
  option erase canonical distinction.
- `recording_date` is independent and cannot be inferred from either.

### `lyrics_languages` versus `vocal_languages`

V2 `lyrics_languages` is derived from MusicBrainz Recording-to-Work lyric
languages. A composition's lyric language is useful evidence but is not always
proof of the language sung in a particular recording: translations,
instrumentals and alternate-language performances exist.

- Keep `lyrics_languages` and its existing values as a compatibility field.
- Introduce `vocal_languages` as the V3 recording-level canonical field.
- A field-specific resolver may use reliable Work/lyrics evidence, performance
  relationships and other future sources, but migration cannot bulk-copy or
  rename the old field.
- `artist_languages`, release `language`, artist geography and title script are
  ineligible for automatic promotion.

### `cover` versus typed artwork

- Existing `fields.cover`, `cover.jpg`, `artpath` and one embedded Front are
  retained as Front compatibility state.
- V3's Front candidate can keep or replace only under existing policy and
  verified asset planning.
- Back and disc assets are additive. Do not rename `cover.jpg` to a generic
  `front.jpg`, because that would break established tooling and paths.
- Existing untyped MP4 artwork may be treated as current Front by the V2
  compatibility convention only; it cannot prove type for additional images.

### BPM and future methodology

- Existing positive finite BPM remains canonical current state, including the
  project's float DB representation.
- If no method/version exists, record internal origin as legacy/unknown when
  such state is introduced; do not fabricate provider/local provenance.
- Future half/double-tempo resolution and methodology changes apply to new
  evidence. They do not silently reinterpret or recompute every V2 value.
- Fractional BPM remains DB-safe and file-write-blocked where MediaFile requires
  integer output.

### Genres, styles, and moods

- Preserve values, ordered lists, taxonomy, aliases, count settings and the
  existing specialized resolvers.
- Do not remap mood to Energy or infer style/genre from new providers without
  the classifier.
- Existing Noqlen private file tags remain readable/write-compatible under the
  V2 contract. They are not precedent for new V3 private tags.

### MusicBrainz IDs and AcoustID

- Keep all four MBID fields identical and separate from ordinary enrichment.
- Existing IDs remain current state/acquisition hints, never evidence in favor
  of repairing themselves.
- Keep AcoustID `reuse_existing`, `fpcalc`, lookup, cache, pacing and explicit
  fingerprint authority unchanged unless separately amended.
- New ISRC/Work evidence may follow an established recording identity but cannot
  mutate MBIDs or turn AcoustID into a provider.

### Existing lyrics

- Identical provider content produces no change.
- A clearly superior representation may be proposed; materially different
  plausible text is REVIEW.
- Existing `.lrc` is preserved and never overwritten merely because LRCLIB has
  a candidate.
- Plain lyrics and synchronized lyrics are related but not aliases.

## Safe aliases

- Keep `fields.cover` as Front-artwork enablement for V2 configs.
- Keep legacy scalar `style` as the existing read fallback to plural `styles`.
- Keep `year` as the edition-year projection of current `date`.
- Keep existing provider names and all valid V2 provider subtrees.
- Keep current CLI modes and AcoustID option/config names.

An alias must preserve semantics and must not cause new provider calls or writes
without the same field/domain authority.

## Prohibited automatic renames or promotions

- `year` -> `original_year` or `recording_date`.
- `lyrics_languages` -> `vocal_languages`.
- `artist_languages`, release language, country or script -> vocal language.
- `cover`/untyped image -> Back or disc artwork.
- title suffix -> edition or track version/mix without evidence.
- scalar native `isrc` -> proof that only one ISRC exists.
- MB recording ID -> Work/ISWC without exact relationship lookup.
- AcoustID recording result -> any MBID write.
- mood/rank/popularity -> Energy or Danceability.
- existing BPM -> a claimed new analyzer methodology version.

## Configuration migration policy

1. Load the complete V2 tree unchanged.
2. Apply compatible aliases in memory and retain the original key in diagnostic
   context.
3. New V3 fields default absent/disabled according to their approved public
   configuration design; provider enablement alone does not enable them.
4. Preserve custom V2 authority for unchanged fields. New roles require an
   explicit documented overlay, not positional guessing where semantics differ.
5. Warn once for a deprecated alias only after its replacement is available and
   semantically equivalent.
6. Reject only genuinely unsafe ambiguity with a precise message; never request
   a config reset.

## Migration verification required later

- Load representative synthetic V2 configurations without modification.
- Open temporary V2 libraries containing each persisted V2 field and preserve
  values through preview/apply/write.
- Verify `year`, lyrics languages, Front artwork, fractional BPM, semantic
  lists, MBIDs, AcoustID and lyrics independently.
- Verify missing V3 fields remain absent rather than false/empty fabricated
  values.
- Verify new fields do not cause provider acquisition when disabled.
- Verify no migration deletes existing tags/assets or requires reimport.
