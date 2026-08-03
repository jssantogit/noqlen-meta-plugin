# Handoff

## State

Noqlen Meta 1.0.0 is released and the post-release state is synchronized on
`main`. Block 029 is now active only as a planning/specification block on branch
`planning/029-acoustid-identity-evidence`.

No AcoustID production code, package dependency, command flag, version bump,
tag, or publication change has been made.

## Block 029 Goal

Add conservative AcoustID/Chromaprint recording evidence for existing-library
Albums and singletons. The subsystem should reuse or explicitly calculate
fingerprints, perform bounded AcoustID lookup, preview and optionally store
AcoustID fields in the beets database, and let decisive recording evidence
filter incompatible complete MusicBrainz release candidates.

## Planning Artifacts

- Requirements:
  `docs/specs/029-acoustid-identity-evidence/requirements.md`
- Design:
  `docs/specs/029-acoustid-identity-evidence/design.md`
- Forge-to-Meta parity matrix:
  `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- Implementation task sequence:
  `docs/specs/029-acoustid-identity-evidence/tasks.md`
- Proposed architecture decision:
  `docs/adr/0025-acoustid-recording-evidence.md`

## Audited Baselines

### Noqlen Forge Core

The Forge implementation already:

- reuses existing fingerprints or runs `fpcalc`;
- performs AcoustID lookup;
- checks score, duration, title, and artist;
- produces AcoustID IDs and MusicBrainz recording candidates;
- reports missing key/backend conditions;
- tests common score, conflict, and tool boundaries.

The Forge implementation also contains shortcuts that are rejected for Meta:

- AcoustID participates as a generic metadata authority;
- the lookup uses a URL containing the complete fingerprint;
- result selection collapses competing groups too early;
- release, release-group, and release-track identity can be derived from the
  first release/medium/track attached to a recording;
- provider plans can write MusicBrainz and file-tag fields;
- force paths can permit overwrites;
- generated fingerprint derivation is not tied to Meta's stale-source model.

### Noqlen Meta 1.0.0

The Meta baseline already provides:

- separate ordinary enrichment and MusicBrainz identity subsystems;
- immutable complete MusicBrainz release/track identity values;
- deterministic global local-to-candidate track assignment;
- structural release scoring and explicit minimum score, pair, completeness,
  ambiguity, and margin gates;
- importer and existing-library identity mapping/application boundaries;
- exact stale database snapshots;
- specialized fail-closed identity-tag file synchronization;
- safe provider transports, process-local caches, and sanitized previews.

AcoustID must extend those contracts rather than bypass them.

## Frozen Planning Decisions

### System role

AcoustID is a separate identity-evidence subsystem. It is not added to the
ordinary provider registry and does not emit ordinary `MetadataCandidate`
values.

### Initial scope

- Existing-library Albums and singletons only.
- Dedicated AcoustID preview mode, provisionally `--acoustid`.
- Explicit missing-fingerprint authority, provisionally
  `--fingerprint-missing`.
- Database apply may store only `acoustid_id` and
  `acoustid_fingerprint` on supported Items.
- No audio-file writes.
- Importer fingerprinting and autotagger candidates remain owned by native
  beets `chroma` and are deferred.

### Recording versus release identity

AcoustID may produce decisive evidence for a MusicBrainz recording MBID. It
cannot directly choose or write:

- MusicBrainz release MBID;
- MusicBrainz release-group MBID;
- MusicBrainz release-track MBID.

Complete four-field identity continues to come from a complete
`MusicBrainzReleaseIdentity` selected by the existing audit.

### Identity integration

- Existing structural evaluations and assignments are calculated unchanged.
- Decisive AcoustID recording evidence filters candidate compatibility after
  assignment.
- Evidence adds no score.
- It cannot rescue weak structure, weak pair assignment, incomplete assignment,
  an ambiguous assignment, or insufficient release margin.
- Unavailable, no-match, and ambiguous evidence is neutral.
- When decisive evidence rejects every candidate, the audit remains ambiguous
  and not repair-ready.

### Fingerprint behavior

- Reuse valid existing beets fingerprints first.
- Do not discover or require a backend when every selected Item already has a
  fingerprint.
- Calculate missing fingerprints only with explicit authority.
- Use an injected bounded Chromaprint backend.
- Generated fingerprints retain a no-follow source-file snapshot and cannot be
  applied after the source changes.
- Never display a full fingerprint, backend output, command path, or private
  media path.

### Service boundary

- Official AcoustID v2 lookup through bounded HTTPS POST.
- Request recording-level metadata only.
- Dedicated `NOQLENMETA_ACOUSTID_API_KEY` environment value.
- Sequential pacing, bounded timeout/bytes/counts/cache, and sanitized errors.
- Preserve bounded competing result groups until minimum score, unique
  recording, and minimum margin are proven.
- No fingerprint submission.

### Application safety

- Preview writes nothing.
- Plan all selected targets before the first store.
- Re-fetch and verify exact database snapshots before mutation.
- Re-verify generated source-file snapshots before mutation.
- Existing non-empty conflicts remain review blockers.
- No force or partial identity behavior.
- Native beets behavior remains responsible for any later generic tag sync.

## Remaining Planning Gates

- Review and approve the parity matrix, requirements, design, and ADR 0025.
- Mark ADR 0025 Accepted only after reviewer PASS.
- Freeze final command and configuration names.
- Complete the backend compatibility spike before selecting an optional Python
  dependency or changing `pyproject.toml`.

## First Implementation Stage After Approval

Begin with immutable domain, policy, and configuration contracts only:

1. AcoustID UUID/result/evidence values and invariants;
2. score/margin/ambiguity policy;
3. fresh safe configuration defaults and validation;
4. redacted representations and safe machine reasons;
5. focused offline tests.

Do not begin transport, subprocess, database application, identity integration,
packaging, or public documentation in that first stage.

## Stop Condition

The planning branch stops after its PR is green and reviewed. Do not add product
code, dependencies, version changes, tags, or release behavior before the
planning PR is merged and ADR 0025 is accepted.
