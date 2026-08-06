# Block 029 Tasks

## Planning And Review

- [x] Audit the current Forge Core AcoustID implementation and tests.
- [x] Audit the Meta Plugin provider, identity, library, application, packaging,
  command, and documentation boundaries.
- [x] Review the official AcoustID lookup contract, Chromaprint backend model,
  and native beets `chroma` coexistence constraints.
- [x] Record the Forge-to-Meta parity matrix.
- [x] Write requirements and architecture for recording-level evidence.
- [x] Propose and accept ADR 0025.
- [x] Freeze final public option and configuration names before product code.
- [x] Freeze domain, lookup, evidence, mapping, preview, and coexistence
  contracts in `contracts.md`.
- [x] Resolve initial lookup metadata to `recordingids` and keep title, artist,
  duration, position, and release scoring exclusively in the MusicBrainz audit.
- [x] Record that repository work from this chat is documentation-only.
- [x] Define, review, and merge the Stage 01 domain, evidence-policy,
  configuration, privacy, test, allowlist, and reviewer brief.
- [x] Implement Stage 01 externally, resolve reviewer findings, pass CI, and
  squash-merge the foundation.
- [x] Record Stage 01 completion and synchronize context and handoff.
- [x] Audit the established fresh identity-library selector for Stage 02 reuse.
- [x] Compare direct bounded `fpcalc` execution with the optional Python wrapper.
- [x] Select direct bounded `fpcalc` without a new Python dependency.
- [x] Define the Stage 02 existing-value, target-selection, fingerprint-backend,
  snapshot, privacy, test, allowlist, and reviewer brief.

## Completed Stage 01: Domain And Policy

- [x] Add immutable AcoustID UUID, result-group, fingerprint-material,
  source-snapshot, track-evidence, and policy domain values.
- [x] Validate strings, UUIDs, scores, margins, durations, counts, and verdict
  invariants.
- [x] Ensure fingerprint-bearing values have redacted representations.
- [x] Add decisive, ambiguous, no-match, and unavailable classification tests.
- [x] Add boundary tests for score, margin, competing recordings, malformed
  groups, deterministic ordering, and verdict invariants.
- [x] Reject conflicting duplicate AcoustID result groups.
- [x] Require eligible counts, top support, runner-up support, and margin to
  agree with retained result groups.
- [ ] Add `AcoustIDTargetResult` only in the later workflow stage that also owns
  exact database snapshots and plans.

## Completed Stage 01: Internal Configuration

- [x] Add an internal fresh AcoustID settings/default factory with the subsystem
  disabled and the exact frozen values.
- [x] Validate every boolean, integer, finite-number, threshold, count, timeout,
  rate, cache, and non-empty `fpcalc` setting.
- [x] Keep the client key outside settings and avoid environment access.
- [ ] Integrate the frozen AcoustID subtree into the public plugin default tree
  only when command and public documentation integration are delivered together.
- [ ] Resolve `NOQLENMETA_ACOUSTID_API_KEY` only in the future service stage.
- [ ] Add the dedicated AcoustID command mode and explicit missing-fingerprint
  authority in the future command stage.
- [ ] Reject unsafe mode combinations before target selection in the future
  command stage.
- [ ] Update command/configuration drift contracts in the future command stage.

## Active Stage 02: Existing Values And Target Selection

- [ ] Add AcoustID-specific immutable Album/singleton target kinds and selected
  Item/target values.
- [ ] Reuse the existing fresh identity-library selector without modifying or
  duplicating it.
- [ ] Convert complete fresh Albums and singletons to AcoustID-specific targets.
- [ ] Preserve stable `library-item:<id>` local keys.
- [ ] Preserve Album-ID, singleton-ID, and disc/track/Item deterministic order.
- [ ] Validate exact supported `Library`, `Album`, and `Item` types.
- [ ] Refresh selected targets and reject missing targets or changed membership.
- [ ] Retain media paths privately and exclude them from representations and
  exceptions.
- [ ] Add `missing`, `valid`, and `malformed` stored-value states.
- [ ] Read and validate existing beets `acoustid_id` and
  `acoustid_fingerprint` fields.
- [ ] Canonicalize only valid AcoustID UUIDs and never treat a stored ID as fresh
  recording evidence.
- [ ] Reuse a valid existing fingerprint only with a finite positive Item
  duration.
- [ ] Prove that a valid reusable fingerprint avoids stat, backend factory,
  executable resolution, and subprocess work.
- [ ] Prove that unauthorized missing or unusable material avoids all filesystem
  and backend work.
- [ ] Add Album, singleton, duplicate-query, ordering, membership-change,
  missing-field, malformed-value, and privacy tests at supported beets
  boundaries.

## Active Stage 02: Fingerprint Backend

- [x] Complete the supported-Python/backend decision between direct `fpcalc` and
  an optional Python wrapper.
- [x] Select direct `fpcalc` with no `pyacoustid` dependency.
- [ ] Add an injectable `FingerprintBackend` protocol and redacted backend
  result.
- [ ] Add a lazy backend factory used only for explicitly authorized generation.
- [ ] Invoke the configured executable with exactly:
  `<fpcalc> -json -length 120 -- <private path>`.
- [ ] Use one argument vector, `shell=False`, and disconnected stdin.
- [ ] Add a timeout-bounded subprocess runner.
- [ ] Drain stdout and stderr concurrently.
- [ ] Cap retained stdout at 1 MiB and retained stderr at 64 KiB.
- [ ] Terminate and then kill after bounded grace on timeout or output overflow.
- [ ] Remove `NOQLENMETA_ACOUSTID_API_KEY` from the child environment without
  logging or persisting its value.
- [ ] Require zero exit status and strict bounded UTF-8 JSON parsing.
- [ ] Validate finite positive duration and non-empty bounded fingerprint.
- [ ] Map missing executable to `fingerprint_backend_unavailable`.
- [ ] Map timeout, overflow, non-zero exit, malformed output, and invalid values
  to `fingerprint_failed`.
- [ ] Sanitize every backend error so it contains no path, command, executable,
  key, fingerprint, stdout, stderr, or raw operating-system exception.
- [ ] Add fake-runner production-backend tests and generic bounded-runner tests
  without requiring an actual `fpcalc` binary in CI.

## Active Stage 02: Source Snapshots And Preparation

- [ ] Acquire no-follow source snapshots containing device, inode, size, and
  nanosecond mtime only.
- [ ] Reject symlinks, directories, non-regular files, malformed stat values,
  and unsupported no-follow semantics.
- [ ] Acquire snapshots immediately before and after backend execution.
- [ ] Require exact pre/post equality before generated material exists.
- [ ] Return `stale_source_file` and discard generated output on mismatch.
- [ ] Add a separate exact snapshot verification helper for a later application
  stage.
- [ ] Build generated `AcoustIDFingerprintMaterial` only after stable snapshots.
- [ ] Build reused material without any source snapshot.
- [ ] Add lazy preparation results with exact stable reasons.
- [ ] Prove that no preparation outcome exposes private material.

## Completed Stage 01: Evidence Classification

- [x] Normalize bounded AcoustID groups to AcoustID UUID plus canonical recording
  MBID sets.
- [x] Ignore release, release-group, medium, and release-track payload data.
- [x] Aggregate support by recording using the highest eligible group score;
  duplicate result groups do not accumulate support.
- [x] Apply minimum score, minimum margin, and unique-top-recording policy.
- [x] Produce stable path-free machine reasons.
- [x] Prove that conflicting high-scoring recording mappings remain ambiguous.
- [x] Prove that local textual metadata and duration do not create or adjust an
  AcoustID verdict.
- [ ] Parse and normalize bounded service payloads only in the future HTTPS
  transport stage.

## Future Stage: AcoustID HTTPS Transport

- [ ] Add an injectable HTTPS form-POST lookup transport.
- [ ] Resolve `NOQLENMETA_ACOUSTID_API_KEY` only at the service boundary.
- [ ] Request only `meta=recordingids`.
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

## Future Stage: Preview, Mapping, And Application

- [ ] Render path-free and fingerprint-free track and target summaries.
- [ ] Map only `acoustid_id` and `acoustid_fingerprint` to standalone AcoustID
  database plans.
- [ ] Add `AcoustIDTargetResult` with selected target, exact database snapshot,
  per-track evidence, plan, and generated-source snapshots.
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

## Future Stage: MusicBrainz Identity Integration

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

## Future Stage: Command And Public Configuration

- [ ] Add `--acoustid` and `--fingerprint-missing` with frozen authority.
- [ ] Compose safely with `--apply` and `--all`.
- [ ] Reject frozen invalid option combinations before selection or local work.
- [ ] Integrate the exact AcoustID subtree into `configuration.default_config()`.
- [ ] Update command, configuration, and documentation drift checks.
- [ ] Keep preview as the default and application database-only.

## Packaging And Compatibility

- [x] Keep Stage 01 and Stage 02 planning free of new AcoustID dependencies.
- [ ] Keep base installation free of unnecessary AcoustID dependencies.
- [ ] Test Python 3.10-3.14 and beets `>=2.12,<3` boundaries.
- [ ] Build wheel and sdist and inspect optional dependency metadata and archive
  contents after the full feature is integrated.
- [ ] Clean-install base, Discogs, and AcoustID-capable variants as applicable.
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
  user-facing entries during public feature integration.
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
