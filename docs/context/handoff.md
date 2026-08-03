# Handoff

## State

Noqlen Meta 1.0.0 is released. Block 029 planning was approved, passed CI, and
was squash-merged to `main` as commit
`6ad71d68347e23cecd45225900a10a8287acca54`.

The current branch, `docs/029-acoustid-contract-freeze`, is documentation-only.
It accepts ADR 0025 and freezes the implementation contracts. No production
code, test, dependency, package metadata, workflow, version, tag, or release
change belongs here.

## Documentation-Only Chat Rule

Repository changes performed from the project chat are limited to:

- specifications;
- ADRs;
- context and handoff documents;
- documentation-only PR administration.

Implementation must happen outside this chat after the corresponding contract
has been approved.

## Block 029 Goal

Add conservative AcoustID/Chromaprint recording evidence for existing-library
Albums and singletons. The subsystem will reuse or explicitly calculate
fingerprints, perform bounded AcoustID lookup, preview and optionally store
AcoustID fields in the beets database, and let decisive recording evidence
filter incompatible complete MusicBrainz release candidates.

## Normative Artifacts

- Requirements:
  `docs/specs/029-acoustid-identity-evidence/requirements.md`
- Design:
  `docs/specs/029-acoustid-identity-evidence/design.md`
- Forge-to-Meta parity matrix:
  `docs/specs/029-acoustid-identity-evidence/parity-matrix.md`
- Frozen implementation contracts:
  `docs/specs/029-acoustid-identity-evidence/contracts.md`
- Task sequence:
  `docs/specs/029-acoustid-identity-evidence/tasks.md`
- Accepted architecture decision:
  `docs/adr/0025-acoustid-recording-evidence.md`

`contracts.md` is normative when provisional text in the earlier planning docs
differs.

## Accepted Architecture

AcoustID is a separate identity-evidence subsystem. It is not added to the
ordinary provider registry and does not emit ordinary `MetadataCandidate`
values.

The first implementation scope is:

- existing-library Albums and singletons;
- reuse of valid beets AcoustID fields;
- explicit missing-fingerprint calculation;
- bounded AcoustID lookup;
- path-free and fingerprint-free preview;
- database-only storage of `acoustid_id` and `acoustid_fingerprint`;
- optional recording compatibility filtering for the existing MusicBrainz
  identity audit.

Explicit exclusions remain:

- importer autotagger duplication;
- fingerprint submission;
- direct audio-file writes;
- direct MusicBrainz writes from AcoustID;
- release, release-group, medium, or release-track inference from provider data;
- force or partial identity behavior.

## Frozen Command Contract

New intended options:

```text
--acoustid
--fingerprint-missing
```

They compose only with existing `--apply` and `--all` as defined in
`contracts.md`.

`--acoustid` is incompatible with:

```text
--identity
--identity-tags
--write
--partial
```

`--fingerprint-missing` is invalid without `--acoustid`.

No new force option exists.

## Frozen Configuration Contract

The intended subtree is:

```yaml
acoustid:
  enabled: false
  reuse_existing: true
  compute_missing: false
  lookup: true
  use_for_identity: true
  min_score: 0.90
  min_margin: 0.05
  max_results: 5
  max_recordings_per_result: 10
  timeout_seconds: 15.0
  requests_per_second: 3.0
  cache_entries: 256
  fpcalc: fpcalc
```

The exact environment variable is:

```text
NOQLENMETA_ACOUSTID_API_KEY
```

Block 029 identity mode may reuse stored fingerprints but never calculates a
missing fingerprint. Calculation authority exists only in standalone AcoustID
mode through configuration or `--fingerprint-missing`.

## Frozen Service And Evidence Contract

Lookup uses form-encoded HTTPS POST to the AcoustID v2 lookup endpoint with:

```text
meta=recordingids
format=json
```

The classifier retains only AcoustID UUIDs, scores, and canonical MusicBrainz
recording MBIDs.

Recording support is the highest eligible group score for that recording.
Duplicate groups do not accumulate support. Decisive evidence requires:

- at least one result at or above `min_score`;
- one unique top recording MBID;
- no equal top competitor;
- `min_margin` over a different runner-up recording when one exists.

Title, artist, duration, position, track assignment, structural score, and
release margin are not duplicated in the AcoustID classifier. They remain in
the existing MusicBrainz audit.

## MusicBrainz Integration Boundary

Complete MusicBrainz release candidates are acquired, assigned, and scored
unchanged. Decisive AcoustID evidence is then used only as a compatibility
filter against the recording MBID already assigned to each local track.

AcoustID:

- adds no score;
- changes no score component;
- cannot rescue a weak candidate;
- cannot create four-field findings;
- cannot write a MusicBrainz field.

When decisive evidence rejects every candidate, the audit remains ambiguous
with reason:

```text
acoustid_recording_conflict
```

Unavailable, no-match, and ambiguous acoustic evidence is neutral.

## Application Boundary

Standalone application may map only:

```text
acoustid_id
acoustid_fingerprint
```

The complete command application is planned before the first write. Stale
selection, membership, path, database state, current values, or generated
source-file snapshots block the complete application unit before mutation.

No audio file is written.

## Next External Implementation Stage

The first implementation stage, outside this chat, is limited to:

1. immutable AcoustID domain values;
2. evidence verdict and policy validation;
3. frozen configuration defaults and validation;
4. redacted representations and safe machine reasons;
5. focused offline domain/configuration tests.

Do not include in that first stage:

- fingerprint subprocess execution;
- network transport;
- library database application;
- MusicBrainz compatibility filtering;
- package dependency changes;
- public documentation changes;
- version or release work.

## Stop Condition

This documentation branch stops after contract review, green CI, and squash
merge. No product implementation is performed from this chat.
