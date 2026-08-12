# Changelog

All notable user-facing changes are recorded here.

## Unreleased

## 2.0.0 - 2026-08-11

### Added

- Release, track, and artist semantic enrichment, including lossless multivalued
  styles and moods plus lyrics language, artist language, country, and area.
- Genre taxonomy and style promotion for broader, consistent genre enrichment.
- Ordinary verified file synchronization for supported metadata and BPM tags
  behind `--apply --write`.
- Cover Art Archive album artwork through verified `cover.jpg` sidecars,
  `Album.artpath`, multidisc handling, and optional embedding.
- Opt-in local BPM analysis through the `[audio]` extra and lazy Librosa backend.
- Existing-library AcoustID evidence workflow for complete Albums and standalone Items.
- `beet nm --acoustid` preview mode with optional database-only `--apply`.
- `--fingerprint-missing` authority for explicitly calculating missing fingerprints in standalone AcoustID mode.
- Reuse of valid stored AcoustID fingerprints and bounded `fpcalc` generation with source-file stability checks.
- Bounded AcoustID `recordingids` lookup using the environment-only `NOQLENMETA_ACOUSTID_API_KEY` credential.
- Optional AcoustID recording-compatibility filtering for existing-library `--identity` when enabled by configuration.
- Public `acoustid` configuration for reuse, lookup, evidence thresholds, pacing, cache size, and `fpcalc` location.

### Changed

- Ordinary `--apply` remains the database mutation authority and may also write
  authorized verified `cover.jpg` sidecars and persist `Album.artpath`, but it
  does not mutate audio files without `--write`.
- Adding `--write` authorizes supported audio-file synchronization and prepared
  artwork embedding without adding provider calls or analyzer work.
- Local BPM analysis is disabled by default and preserves an existing BPM unless
  explicit recalculation is configured.

### Safety

- Preview remains non-mutating, and artwork selection remains separate from
  verified binary application.
- Identity and AcoustID workflows remain isolated from ordinary enrichment, and
  there is no force mode.
- AcoustID is recording-level evidence only: it does not add MusicBrainz structural score, select a release occurrence by itself, or relax identity gates.
- `--identity` never calculates a missing fingerprint, even when standalone missing-fingerprint calculation is configured.
- Standalone AcoustID `--apply` changes only `acoustid_id` and `acoustid_fingerprint` in the beets database and never writes audio files.
- Existing non-empty AcoustID conflicts, stale database targets, and changed generated source files block before the first write.
- Fingerprints, private media paths, API keys, backend output, and raw provider exceptions remain excluded from public output.
- Native beets `chroma` continues to own importer acoustic matching and fingerprint submission; Noqlen adds no importer AcoustID autotagger path.

## 1.0.0 - 2026-08-02

### Added

- Importer enrichment for selected releases and selected-track plain lyrics.
- Existing-library album enrichment with strict and partial database policies.
- Separate importer and library MusicBrainz identity audit/repair workflows.
- Specialized synchronization of four coherent MusicBrainz IDs to FLAC, MP3,
  M4A/MP4, Ogg Vorbis, and Opus tags.
- Discogs, anchored MusicBrainz, Last.fm, iTunes, and LRCLIB adapters.
- A beginner-first MkDocs manual and package/release validation.
- Tested package support bounded to Python 3.10 through 3.14.
- Distribution under the MIT License.

### Safety

- Preview is the default and each mutation surface requires explicit authority.
- Resolver reviews and lossy mappings are never silently accepted.
- Identity repair has no partial or force mode.
- File synchronization plans all targets first, verifies same-directory
  candidates, replaces one file atomically, and verifies the committed result.
- Provider errors, malformed identifiers, lyrics, tokens, and private paths are
  not exposed in public output.
