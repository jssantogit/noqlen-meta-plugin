# Block 029 AcoustID Parity Matrix

This matrix compares the current Noqlen Forge Core behavior with the decision
for Noqlen Meta. `Adapt` means retain the capability behind Meta's stricter
boundaries. `Reject` means the Forge behavior is incompatible with the plugin's
identity model. `Defer` means it is outside the first AcoustID update.

| Capability | Forge Core behavior | Meta decision | Reason | Block 029 state |
| --- | --- | --- | --- | --- |
| Provider role | Generic metadata provider with identifier authority | Adapt as a separate identity-evidence subsystem | Acoustic evidence belongs to a concrete file and must not enter ordinary field resolution | Required |
| Existing fingerprint reuse | Reuses an existing fingerprint before calculation | Keep and strengthen | Avoid duplicate CPU work and cooperate with beets `chroma` | Required |
| Backend requirement | Resolves `fpcalc` before processing the target | Redesign | A backend is unnecessary when every selected Item already has a valid fingerprint | Required |
| Missing fingerprint | Automatically runs `fpcalc` when possible | Redesign as explicit | Whole-library or unrelated commands must not silently perform expensive audio work | Required |
| Fingerprint backend | Direct `fpcalc -json` subprocess | Adapt behind an injected bounded backend | Preserve portability testing, timeouts, output bounds, and sanitized failure | Required |
| Fingerprint persistence | Can write fingerprint tags through provider plans | Database-only in AcoustID mode | Noqlen must not add another direct generic file writer | Required |
| Missing client key | Generates fingerprint and skips lookup with warning | Keep | Local work remains useful and unrelated workflows continue | Required |
| Client key sources | Accepts generic environment/config keys | Redesign to dedicated environment variable | Avoid secret drift and accidental disclosure | Required |
| Lookup method | GET URL containing the complete fingerprint | Reject | Long fingerprints and credentials must not enter displayed/loggable URLs | Required |
| Lookup endpoint | AcoustID v2 lookup | Keep through HTTPS POST | Use the official service while preserving privacy and bounds | Required |
| Request pacing | No dedicated AcoustID pacing in the adapter | Add | The service boundary needs explicit sequential rate control | Required |
| Timeout | Generic HTTP timeout | Keep and validate | External work must remain bounded | Required |
| Response size | Generic JSON read bound | Keep and specialize | Fingerprint results need strict service-specific schema and count bounds | Required |
| Process cache | No dedicated bounded lookup cache | Add | Avoid duplicate lookups inside one command without storing raw provider payloads | Required |
| Minimum score | Configurable, default 0.80 | Adapt with stricter reviewed default and validation | Evidence used near identity repair needs conservative thresholds | Required |
| Candidate bound | Truncates result list | Keep plus per-result recording bound | Prevent provider response amplification | Required |
| Result selection | Chooses one highest combined row | Redesign | Full bounded competing result groups are needed to prove uniqueness and margin | Required |
| Title/artist checks | Add score and influence confidence | Keep only as corroboration or veto | Local text can reject an implausible result but cannot create acoustic identity | Required |
| Duration check | Raises or lowers confidence | Keep with explicit hard mismatch policy | Duration is relevant corroboration and must have boundary tests | Required |
| AcoustID ID | Writes a selected AcoustID ID | Adapt | May be proposed only from decisive evidence and may not overwrite conflicts | Required |
| Recording MBID | Writes `mb_track_id` directly | Reject as standalone write authority | Recording evidence must pass through the complete MusicBrainz identity audit | Required |
| Release selection | Takes release data attached to a recording | Reject | A recording can appear on many releases | Required |
| Release-track selection | Takes the first release/medium/track occurrence | Reject | Release-track identity is occurrence-specific and first-result selection is unsafe | Required |
| Release-group selection | Derives from selected recording release data | Reject | Release-group identity follows a complete selected MusicBrainz release | Required |
| Album consistency | Writes album IDs when all track rows share one release | Redesign | Only complete MusicBrainz release candidates may establish album-wide identity | Required |
| Identity influence | AcoustID can be field authority for MusicBrainz IDs | Redesign as candidate compatibility filter | Evidence may reject incompatible assignments but cannot rescue weak structure | Required |
| Structural scoring | Separate metadata-provider scoring | Preserve Meta's existing identity scoring unchanged | Existing score, assignment, and margin contracts remain auditable | Required |
| Existing MBID conflict | Records conflict and may still expose force paths | Reject force; keep review | Identity conflict must remain blocked until complete evidence is selected | Required |
| Force overwrite | Supports general and identity-specific force options | Reject | Noqlen Meta has no force mode and ambiguity cannot be waived | Required |
| Direct audio-file writes | Generates per-file write plans | Reject | AcoustID mode writes no files; native beets behavior owns later synchronization | Required |
| All-plan application | Provider flow can create per-track plans | Strengthen | All selected targets and stale snapshots must verify before the first database write | Required |
| Generated-file stale check | No dedicated source-file snapshot tied to fingerprint derivation | Add | A fingerprint must not be stored after the source file changes | Required |
| Preview privacy | Shortens displayed fingerprint in some output | Strengthen to never display fingerprint | Fingerprints, paths, keys, payloads, and backend output stay private | Required |
| Import integration | Generic path flow can process incoming files | Defer to native beets `chroma` | Avoid a second acoustic autotagger and duplicate importer work | Deferred |
| Existing-library mode | Path-based metadata command | Adapt to fresh beets Album/Item targets | Reuse established library selection and stale-state contracts | Required |
| Submission | Not part of lookup flow | Defer explicitly | Submission needs user credentials, consent, and separate privacy design | Deferred |
| Live tests | Provider tests are mostly injected/offline | Keep with explicit opt-in live marker | CI must not depend on service availability or real audio | Required |
| Dependency model | Uses system `fpcalc` directly | Decide after backend compatibility spike | Exact optional Python dependency is packaging policy, not evidence semantics | Planning task |

## Rejected Shortcuts

The following shortcuts are explicitly outside the design:

- copying `AcoustIDMetadataProvider` into the ordinary provider package;
- requesting release data and choosing the first attached release;
- writing any MusicBrainz ID directly from the AcoustID response;
- adding AcoustID confidence points to the existing structural release score;
- silently fingerprinting every selected file;
- using a full fingerprint inside a logged GET URL;
- adding force, partial identity repair, direct file writes, or submission;
- presenting native beets `chroma` and Noqlen AcoustID evidence as the same
  workflow.

## Capabilities Preserved From Forge

The redesign still preserves the useful core ideas:

- reuse existing fingerprints;
- generate missing fingerprints through Chromaprint when explicitly requested;
- look up AcoustID IDs and recording MBIDs;
- combine acoustic score with duration and metadata sanity checks;
- report missing backend/key/service as a safe unavailable condition;
- preserve conflicts rather than silently replacing known identity;
- test score thresholds, mismatch behavior, missing tools, and missing keys.
