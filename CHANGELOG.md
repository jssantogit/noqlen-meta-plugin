# Changelog

All notable user-facing changes are recorded here.

## 1.0.0 - Unreleased

### Added

- Importer enrichment for selected releases and selected-track plain lyrics.
- Existing-library album enrichment with strict and partial database policies.
- Separate importer and library MusicBrainz identity audit/repair workflows.
- Specialized synchronization of four coherent MusicBrainz IDs to FLAC, MP3,
  M4A/MP4, Ogg Vorbis, and Opus tags.
- Discogs, anchored MusicBrainz, Last.fm, iTunes, and LRCLIB adapters.
- A beginner-first MkDocs manual and package/release validation.

### Safety

- Preview is the default and each mutation surface requires explicit authority.
- Resolver reviews and lossy mappings are never silently accepted.
- Identity repair has no partial or force mode.
- File synchronization plans all targets first, verifies same-directory
  candidates, replaces one file atomically, and verifies the committed result.
- Provider errors, malformed identifiers, lyrics, tokens, and private paths are
  not exposed in public output.
