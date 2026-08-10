# Troubleshooting

Each answer starts with the next practical step, then explains the likely
cause and links to the complete behavior.

## Why Did Strict Mode Apply Nothing?

Review every `REVIEW` and `BLOCKED` line in the preview. Strict mode withholds
all ordinary Noqlen changes for one target when any field needs review or
cannot map losslessly. Use [strict and partial](../concepts/strict-vs-partial.md)
to decide whether explicit partial mode is appropriate.

## Why Did Partial Skip One Field?

Read that field's status and leave it unchanged until its conflict or mapping
limit is resolved. Partial applies only already-safe ordinary fields; it does
not accept reviews or reshape blocked values. See the [field reference](../reference/fields.md).

## Is Partial The Same As Force?

Do not use partial to override a warning; address the warning instead. Partial
is not force: it never lowers confidence, chooses ambiguity, bypasses stale
guards, or weakens identity/file checks. Noqlen v1 has no `--force`. See
[strict and partial](../concepts/strict-vs-partial.md#partial-is-not-force).

## Why Did `--apply` Not Change My Audio Files?

Preview native `beet write -p QUERY` if generic file tags should follow the
database. Noqlen `--apply` authorizes database changes only. Read [database,
files, and Navidrome](../concepts/database-files-navidrome.md).

## What Is The Difference Between `beet write` And Identity Tags `--write`?

Use native `beet write` for generic beets database-to-file fields; use Noqlen
identity-tag write only for the verified four-MBID workflow. They have
different scope and safety behavior. See [beets interaction](../reference/beets-interaction.md).

## Why Does `--write` Require `--identity-tags`?

Add `--identity-tags` only when four coherent database MBIDs should replace
their file-tag counterparts. `--write` is deliberately not a generic Noqlen
permission. See the [`--write` reference](../reference/commands.md).

## Why Is MusicBrainz Identity Repair Blocked?

Keep the database unchanged and inspect the preview's score, margin,
assignment, and completeness. Repair requires one unique, strong, complete
candidate and a fresh target. See the [identity guide](../guides/musicbrainz-identity.md).

## Why Did AcoustID Block MusicBrainz Identity Repair?

Keep the database unchanged and inspect the identity preview. When decisive
AcoustID recording evidence contradicts every structurally valid MusicBrainz
candidate, Noqlen returns `acoustid_recording_conflict` rather than choosing a
release anyway. AcoustID only removes incompatible candidates; it does not add
score or relax the normal identity gates. See the [`--identity` reference](../reference/commands.md#identity).

## Why Did AcoustID Not Run During `--identity`?

Check `noqlenmeta.acoustid.enabled`, `use_for_identity`, `lookup`, and whether a
valid stored fingerprint exists. Existing-library identity intentionally never
calculates a missing fingerprint, including when `compute_missing` is true.
Use standalone `--acoustid --fingerprint-missing` when you explicitly want
missing fingerprints calculated. See the [configuration reference](../reference/configuration.md).

## Why Does AcoustID Say The Client Key Is Missing?

Set `NOQLENMETA_ACOUSTID_API_KEY` in the environment that runs beets. The key
is intentionally not a YAML setting and should not be committed to the beets
configuration. Missing credentials make lookup unavailable rather than
exposing or guessing a key.

## Why Did `--fingerprint-missing` Not Change The Database?

Add `--apply` only after reviewing the standalone preview. `--fingerprint-missing`
permits local fingerprint calculation; it does not grant database-write
authority. Standalone AcoustID `--apply` can change only `acoustid_id` and
`acoustid_fingerprint`, never audio files. See the [`--acoustid` reference](../reference/commands.md#acoustid).

## What Is The Difference Between Chromaprint, `fpcalc`, AcoustID, And beets `chroma`?

Use `fpcalc` only when you explicitly need Noqlen to calculate a missing
fingerprint. Chromaprint is the fingerprint algorithm/tooling family, `fpcalc`
is its local executable, and AcoustID is the lookup service that maps a
fingerprint to recording evidence. Native beets `chroma` remains responsible
for importer acoustic matching and fingerprint submission. Noqlen's AcoustID
feature operates on existing-library targets and does not replace `chroma`.

## Why Did One Matching Track Select The Complete Album?

Narrow the Item query if you selected the wrong album, then preview again.
Identity consistency is album-wide, so matching any album Item expands to the
complete Album once. See [query semantics](../reference/commands.md#query-semantics).

## Why Was A Singleton Included?

Check whether the matching Item has no Album association. Identity,
standalone AcoustID, and identity-tag modes support standalone Items, including
through `--all`. Ordinary enrichment remains Album-only. See the [command
reference](../reference/commands.md).

## Why Is Database Identity Incomplete?

Run `beet nm --identity QUERY` and repair only if the result is ready. The
identity-tag workflow requires complete coherent release, release-group,
recording, and release-track IDs before it can trust the database. See the
[identity-tag guide](../guides/identity-tags.md).

## Why Was My File Reported Unsupported?

Keep the file unchanged and confirm it is one of the tested formats with a
regular single-link source. MediaFile support alone does not prove the safe
replacement workflow. See [media compatibility](../reference/compatibility.md#media-formats).

## Why Did Identity-Tag Mode Block On My Operating System Or Filesystem?

Use database-only workflows, or move the operation to a supported environment
without changing the source first. Identity-tag replacement requires
`O_NOATIME`, `O_NOFOLLOW`, safe metadata preservation, and same-directory
atomic replacement. Unsupported guarantees block before writing. See
[operating systems and filesystems](../reference/compatibility.md#operating-systems-and-filesystems).

## Why Does Navidrome Still Show Old Metadata?

Confirm the file tags changed, then allow or request a Navidrome rescan using
Navidrome's own administration. `nm --apply` and `nm --acoustid --apply` change
only the beets database, and Navidrome scans can be delayed or cached. Follow
the [Navidrome guide](../guides/navidrome.md).

## Why Did An Enabled Provider Contribute Nothing?

Check field enablement, provider capability, authority, confidence, and the
required identity. An enabled provider is called only when all these controls
intersect, and an unavailable service safely contributes nothing. See the
[provider reference](../reference/providers.md).

## Why Is Synchronized Lyrics Not Written?

Leave `synced_lyrics` disabled unless you want to preview its blocked status.
LRCLIB can supply synchronized text, but beets' selected track model has no
lossless v1 target, so Noqlen never collapses it into plain lyrics or writes
SYLT. See the [field reference](../reference/fields.md).

## Where Should I Put The Discogs Token?

Set `NOQLENMETA_DISCOGS_TOKEN` in the environment that runs beets and keep
`user_token` empty in committed examples. A non-empty environment value takes
precedence over YAML, and output redacts token values. Direct release-ID
lookup can work without a token; search generally needs one. See the
[configuration reference](../reference/configuration.md#provider-controls).
