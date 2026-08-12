# Safety Guarantees

Preview is the default. Importer `apply`, ordinary library `--apply`, ordinary
`--write`, identity `--identity --apply`, AcoustID `--apply`, native
`beet write`, and identity-tag `--identity-tags --write` are separate
authorities. None silently grants another, and Noqlen has no force mode.

Noqlen prepares target-aware plans before application. Fresh-state checks catch
stale database values, changed source files, duplicate targets, invalid
mappings, and unsupported lossless representations.

Artwork selection and binary application are separate. Ordinary `--apply` may
write verified `cover.jpg` sidecars and `Album.artpath`; ordinary
`--apply --write` may embed the already selected image. Adding write never
causes another CAA lookup or Librosa analysis.

Ordinary supported audio synchronization and identity-tag synchronization use
verified candidate copies rather than saving source files in place. Candidate
tags are reopened and checked before replacement; committed results are checked
again. Identity-tag mode additionally requires regular single-link files,
atime-safe no-follow reads, safe metadata preservation, same-directory backup,
and atomic replacement.

Targets commit independently where documented. A safely reversible failure
restores and verifies the original. Uncertain committed state is reported
truthfully and may retain a path-private recovery artifact instead of guessing.

Private paths, temporary names, raw malformed IDs, raw lyrics, fingerprints,
credentials, and raw provider errors are excluded from normal public output.
