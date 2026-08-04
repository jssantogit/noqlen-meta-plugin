# Block 029 Tasks

## Planning And Review

- [x] Audit the current Forge Core AcoustID implementation and tests.
- [x] Audit the Meta Plugin provider, identity, library, application, packaging,
  command, and documentation boundaries.
- [x] Review the official AcoustID lookup contract, Chromaprint backend model,
  and native beets `chroma` coexistence constraints.
- [x] Record the Forge-to-Meta parity matrix.
- [x] Write requirements and architecture for recording-level evidence.
- [x] Propose ADR 0025.
- [x] Receive owner approval for the Block 029 scope and ADR after green CI.
- [x] Freeze final public option and configuration names before product code.
- [x] Freeze domain, lookup, evidence, mapping, preview, and coexistence
  contracts in `contracts.md`.
- [x] Resolve initial lookup metadata to `recordingids` and keep title, artist,
  duration, position, and release scoring exclusively in the MusicBrainz audit.
- [x] Record that repository work from this chat is documentation-only.
- [x] Define the external Stage 01 domain, evidence-policy, configuration,
  privacy, test, allowlist, and reviewer brief.

## Domain And Policy

- [ ] Add immutable AcoustID UUID, result-group, fingerprint-material, track-
  evidence, target-result, and policy domain values.
- [ ] Validate all strings, UUIDs, scores, margins, durations, counts, and
  verdict invariants.
- [ ] Ensure fingerprint-bearing values have redacted representations.
- [ ] Add decisive, ambiguous, no-match, and unavailable classification tests.
- [ ] Add boundary tests for score, margin, competing recordings, malformed
  groups, deterministic ordering, and verdict invariants.

## Configuration And Command Contract

- [ ] Add an internal fresh AcoustID settings/default factory with the subsystem
  disabled and the exact frozen values.
- [ ] Validate boolean, integer, finite-number, path, threshold, and count
  settings before backend or network work.
- [ ] Integrate the frozen AcoustID subtree into the public plugin default tree
  only when command and public documentation integration are delivered together.
- [ ] Resolve `NOQLENMETA_ACOUSTID_API_KEY` without logging or persistence.
- [ ] Add the dedicated AcoustID command mode and explicit missing-fingerprint
  authority.
- [ ] Reject unsafe mode combinations before target selection.
- [ ] Update command/configuration drift contracts.

## Existing Values And Target Selection

- [ ] Select complete fresh existing-library Albums and singletons through
  normal beets queries.
- [ ] Retain stable database-ID local keys and deterministic Item order.
- [ ] Read and validate existing beets AcoustID fields.
- [ ] Prove that a valid existing fingerprint avoids backend discovery and
  execution.
- [ ] Preserve an existing AcoustID ID as current state rather than treating it
  as fresh lookup evidence.
- [ ] Add Album, singleton, membership-change, missing-field, and malformed-
  value tests at minimum and latest supported beets.

## Fingerprint Backend

- [ ] Complete a supported-Python/backend spike comparing direct bounded
  `fpcalc` invocation with a narrow optional Python wrapper.
- [ ] Record the selected backend/dependency strategy before package metadata
  changes.
- [ ] Add an injectable production fingerprint backend.
- [ ] Discover the backend only for Items that need authorized calculation.
- [ ] Use no shell and bound runtime, stdout, stderr, and parsed fingerprint
  length.
- [ ] Validate finite positive duration and fingerprint output.
- [ ] Capture no-follow source-file snapshots for generated fingerprints.
- [ ] Sanitize every missing-tool, timeout, execution, parse, and unsupported-
  filesystem outcome.
- [ ] Add fake-backend and generated-media tests across supported formats needed
  for the workflow.

## AcoustID HTTPS Transport

- [ ] Add an injectable HTTPS form-POST lookup transport.
- [ ] Request only recording-level metadata needed by the evidence model.
- [ ] Pace sequential requests within the service ceiling using monotonic time.
- [ ] Bound request bytes, response bytes, timeout, results, recordings, and
  process-local cache entries.
- [ ] Key the cache with a fingerprint digest and duration without exposing raw
  material.
- [ ] Validate status and JSON/schema before normalization.
- [ ] Sanitize HTTP, timeout, rate-limit, oversized, malformed, and service
  failure output.
- [ ] Add deterministic fake-clock, fake-opener, pacing, cache, and failure tests.
- [ ] Keep live service tests optional and excluded from normal CI.

## Evidence Classification

- [ ] Normalize bounded AcoustID groups to AcoustID UUID plus canonical recording
  MBID sets.
- [ ] Ignore release, release-group, medium, and release-track payload data.
- [ ] Aggregate support by recording using the highest eligible group score;
  duplicate result groups do not accumulate support.
- [ ] Apply minimum score, minimum margin, and unique-top-recording policy.
- [ ] Produce stable path-free machine reasons.
- [ ] Prove that a first-release/first-track shortcut cannot enter the model.
- [ ] Prove that conflicting high-scoring recording mappings remain ambiguous.
- [ ] Prove that local textual metadata and duration do not create or adjust an
  AcoustID verdict.

## Preview, Mapping, And Application

- [ ] Render path-free and fingerprint-free track and target summaries.
- [ ] Map only `acoustid_id` and `acoustid_fingerprint` to standalone AcoustID
  database plans.
- [ ] Preserve existing non-empty conflicts as review blockers.
- [ ] Plan every selected target before the first store.
- [ ] Re-fetch and verify exact database target snapshots before mutation.
- [ ] Re-verify generated source-file snapshots before mutation.
- [ ] Block the complete application unit on stale target, membership, path,
  file, or current-value changes.
- [ ] Store only planned Item database fields.
- [ ] Prove that AcoustID mode never writes audio files or MusicBrainz fields.
- [ ] Add success, no-op, conflict, stale-state, and rollback-before-first-write
  workflow tests.

## MusicBrainz Identity Integration

- [ ] Add a pure mapping from decisive AcoustID evidence to local-key recording
  expectations.
- [ ] Add an immutable candidate-compatibility result separate from structural
  score values.
- [ ] Filter structurally evaluated MusicBrainz release candidates only after
  their existing assignments are calculated.
- [ ] Preserve every existing score component and threshold unchanged.
- [ ] Treat unavailable, no-match, and ambiguous evidence as neutral.
- [ ] Return `acoustid_recording_conflict` when decisive evidence rejects every
  candidate.
- [ ] Generate four-field findings only from the selected complete MusicBrainz
  release candidate.
- [ ] Prove that AcoustID cannot rescue weak structure, weak pair assignments,
  incomplete track assignment, or insufficient margin.
- [ ] Cover albums, singletons, repeated recordings, multidisc releases, bonus
  tracks, near ties, and contradictory evidence.

## Packaging And Compatibility

- [ ] Select and bound any optional `acoustid` Python extra only after the
  backend spike.
- [ ] Keep base installation free of unnecessary AcoustID dependencies.
- [ ] Test Python 3.10-3.14 and beets `>=2.12,<3` boundaries.
- [ ] Build wheel and sdist and inspect optional dependency metadata and archive
  contents.
- [ ] Clean-install base, AcoustID-capable, and Discogs-plus-AcoustID variants.
- [ ] Test plugin discovery and command help from built artifacts.

## Documentation And Release Readiness

- [ ] Document AcoustID versus Chromaprint versus beets `chroma`.
- [ ] Document existing-value reuse, explicit calculation, lookup credentials,
  privacy, preview, database apply, and no-file-write boundaries.
- [ ] Add command, configuration, provider/evidence, field, compatibility, and
  troubleshooting coverage.
- [ ] Update README capability and installation summaries without exceeding its
  limit.
- [ ] Replace `No user-facing changes yet` under `Unreleased` with accurate
  user-facing entries during implementation.
- [ ] Update context and handoff after each reviewed implementation stage.
- [ ] Run Ruff, full offline tests, docs checks, strict MkDocs, hygiene,
  distribution validation, and clean-install smoke tests.
- [ ] Obtain final reviewer PASS before version bump, tag, or publication.

## Explicitly Deferred

- [ ] AcoustID fingerprint submission with user credentials and consent.
- [ ] Importer fingerprint generation owned by Noqlen.
- [ ] AcoustID-generated beets autotagger candidates.
- [ ] Direct AcoustID or generic metadata file writes.
- [ ] Force or partial identity repair.
- [ ] Direct release, release-group, or release-track identity from AcoustID.
