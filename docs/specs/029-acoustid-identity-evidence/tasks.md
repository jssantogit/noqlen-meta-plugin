# Block 029 Tasks

## Planning And Review

- [x] Audit the Forge Core AcoustID implementation and tests.
- [x] Audit Meta Plugin provider, identity, library, application, packaging,
  command, and documentation boundaries.
- [x] Review the official AcoustID lookup contract, Chromaprint backend model,
  and native beets `chroma` coexistence constraints.
- [x] Record the Forge-to-Meta parity matrix.
- [x] Write requirements and architecture for recording-level evidence.
- [x] Propose and accept ADR 0025.
- [x] Freeze public option/configuration names and domain, lookup, evidence,
  mapping, preview, privacy, and coexistence contracts.
- [x] Keep initial lookup metadata to `recordingids`; keep textual/release scoring
  in the MusicBrainz identity audit.
- [x] Record that repository work from this chat is documentation-only.
- [x] Define, review, implement externally, validate, and record Stage 01.
- [x] Audit the established fresh identity-library selector for Stage 02 reuse.
- [x] Select direct bounded `fpcalc` with no new Python dependency.
- [x] Define, review, implement externally, validate, and record Stage 02.
- [x] Revalidate the official AcoustID service contract before Stage 03.
- [x] Define and merge the Stage 03 HTTPS transport/lookup brief.
- [x] Implement Stage 03 externally and resolve all external-review findings.
- [x] Pass Stage 03 CI across supported Python/beets, docs, hygiene, and package
  jobs and squash-merge PR #12.
- [x] Record Stage 03 completion and synchronize context and handoff.
- [x] Define and merge the Stage 04 standalone workflow brief.
- [x] Implement/review/merge Stage 04A Planning + Preview through PR #15.
- [x] Implement/review/merge Stage 04B Verified Database Application through PR #16.
- [x] Resolve Stage 04B uncertain-commit reporting before merge.
- [x] Record Stage 04 completion and synchronize context/handoff.
- [ ] Review and merge the single final Stage 05 integration brief.
- [ ] Implement Stage 05 externally as the last Block 029 product stage.
- [ ] Resolve all Stage 05 external-review findings and pass final product CI.
- [ ] Record Stage 05 / Block 029 implementation completion.

## Completed Stage 01: Domain And Internal Configuration

- [x] Add immutable AcoustID UUID, result-group, fingerprint-material,
  source-snapshot, track-evidence, and policy domain values.
- [x] Validate strings, UUIDs, scores, margins, durations, counts, and verdict
  invariants.
- [x] Ensure fingerprint-bearing values have redacted representations.
- [x] Add decisive, ambiguous, no-match, and unavailable classification tests.
- [x] Reject conflicting duplicate AcoustID result groups.
- [x] Require evidence counts/support/margins to agree with retained groups.
- [x] Add internal immutable AcoustID settings/defaults with subsystem disabled.
- [x] Add `AcoustIDTargetResult` in Stage 04A with exact database snapshots and plans.
- [ ] Integrate the exact AcoustID subtree into public plugin defaults in Stage 05.
- [ ] Add dedicated `--acoustid` / `--fingerprint-missing` authority in Stage 05.
- [ ] Reject unsafe public-mode combinations before target selection in Stage 05.

## Completed Stage 02: Existing Values And Target Selection

- [x] Add immutable Album/singleton target kinds and selected Item/target values.
- [x] Reuse the established fresh identity-library selector without modifying or
  duplicating it.
- [x] Convert complete fresh Albums and singletons to AcoustID targets.
- [x] Preserve stable `library-item:<id>` keys and deterministic ordering.
- [x] Validate exact supported `Library`, `Album`, and `Item` types.
- [x] Refresh targets and reject missing targets or changed membership.
- [x] Retain media paths privately and exclude them from representations/errors.
- [x] Validate stored `acoustid_id` / `acoustid_fingerprint` as missing, valid,
  or malformed.
- [x] Never treat a stored AcoustID ID as fresh recording evidence.
- [x] Reuse a valid stored fingerprint only with finite positive duration.
- [x] Prove reusable and unauthorized paths avoid unnecessary filesystem/backend
  work.

## Completed Stage 02: Fingerprint Backend And Source Stability

- [x] Use direct `fpcalc` with no `pyacoustid` dependency.
- [x] Add injectable fingerprint backend and lazy backend factory.
- [x] Invoke exactly `<fpcalc> -json -length 120 -- <private path>`.
- [x] Use argument vector, `shell=False`, and disconnected stdin.
- [x] Bound subprocess timeout, stdout, stderr, terminate, kill, post-kill reap,
  and reader-thread cleanup.
- [x] Use nonblocking concurrent stdout/stderr draining only.
- [x] Remove `NOQLENMETA_ACOUSTID_API_KEY` from the child environment without
  resolving or exposing its value.
- [x] Require zero exit and strict bounded UTF-8 JSON output.
- [x] Map missing executable and backend failures to frozen safe reasons.
- [x] Acquire no-follow regular-file snapshots before and after generation.
- [x] Require exact device/inode/size/mtime equality before generated material
  exists.
- [x] Add later-use exact generated-source verification helper.
- [x] Reject symlinks, non-regular files, malformed stat values, unsupported
  semantics, and changed sources fail-closed.
- [x] Keep normal tests independent of a real `fpcalc` binary/audio fixture.

## Completed Stage 01: Evidence Classification

- [x] Normalize bounded AcoustID groups to AcoustID UUID plus canonical recording
  MBID sets.
- [x] Ignore release, release-group, medium, release-track, and textual metadata.
- [x] Aggregate recording support using highest eligible group score without
  duplicate accumulation.
- [x] Apply minimum score, minimum margin, and unique-top-recording policy.
- [x] Produce stable path-free machine reasons.
- [x] Keep contradictory high-scoring mappings ambiguous.
- [x] Prove local textual metadata/duration do not alter the evidence verdict.

## Completed Stage 03: AcoustID HTTPS Transport And Lookup

- [x] Add injectable HTTPS form-POST lookup transport.
- [x] Resolve `NOQLENMETA_ACOUSTID_API_KEY` only at a real uncached service
  lookup boundary.
- [x] Request only the exact frozen fields with `meta=recordingids` and JSON.
- [x] Use deterministic half-up whole-second duration rounding.
- [x] Keep TLS verification enabled and redirects fail-closed.
- [x] Perform no automatic retry, including for timeout, 429, or 5xx responses.
- [x] Bound complete request bytes at 2 MiB before transport opens.
- [x] Read responses incrementally with a 1 MiB retained-response cap.
- [x] Treat expected HTTP/URL/TLS/timeout/connection/read/size failures as
  `lookup_failed` without raw exception leakage.
- [x] Treat `http.client.HTTPException` / `IncompleteRead` as operational read
  failures and never cache partial/truncated responses.
- [x] Keep unexpected injected/programmer failures distinct and propagate only
  sanitized generic boundary errors.
- [x] Validate strict UTF-8, one JSON value, service status, and retained schema.
- [x] Reject NaN/Infinity and conflicting duplicate result groups.
- [x] Retain only AcoustID UUID, score, and recording MBIDs.
- [x] Apply `max_results` and `max_recordings_per_result` before domain
  construction.
- [x] Reuse the Stage 01 evidence classifier rather than creating another
  scoring algorithm.
- [x] Pace sequential uncached network attempts with monotonic time within the
  configured ceiling of 3 requests/second.
- [x] Ensure disabled lookup, missing credentials, oversized requests, and cache
  hits consume no transport work/rate slot.
- [x] Ensure a network attempt consumes a rate slot once transport is entered.
- [x] Add bounded process-local successful-result caching.
- [x] Key cache entries with framed SHA-256 over fingerprint + rounded duration
  without raw fingerprint/client key exposure.
- [x] Cache no transport, service, parsing, or schema failure.
- [x] Add deterministic fake-clock/fake-transport/request/response/privacy tests.
- [x] Keep normal CI fully offline with no mandatory live service test.

## Completed Stage 04: Planning, Preview, And Verified Database Application

- [x] Define and review one Stage 04 brief split by the mutation boundary.
- [x] Render path-free and fingerprint-free track and target summaries.
- [x] Map only `acoustid_id` and `acoustid_fingerprint` to standalone AcoustID
  database plans.
- [x] Add `AcoustIDTargetResult` with selected target, exact database snapshot,
  per-track evidence, plan, and generated-source snapshots.
- [x] Preserve existing non-empty conflicts as review blockers.
- [x] Capture exact raw malformed current values for stale detection.
- [x] Plan every selected target before the first store.
- [x] Re-fetch and verify exact database target snapshots before mutation.
- [x] Re-verify generated source-file snapshots before mutation.
- [x] Block the complete application unit on stale target, membership, path,
  source-file, current-value, `REVIEW`, or `BLOCKED` state before the first write.
- [x] Reject duplicate target/item identities and noncanonical plans before write.
- [x] Persist only fields marked `PROPOSE` using narrow SQL.
- [x] Isolate unrelated dirty Item state from AcoustID persistence.
- [x] Use per-target savepoints with in-transaction revalidation and rollback.
- [x] Re-read and verify committed values before notifications.
- [x] Notify `database_change` only for successfully committed changed Items.
- [x] Report root transaction uncertainty conservatively without treating savepoint
  release as proof of commit.
- [x] Prove AcoustID Stage 04 never writes audio files or MusicBrainz fields.
- [x] Keep normal tests independent of live network, API keys, real `fpcalc`, and
  audio-file writes.

## Final Stage 05: Identity, Command, And Public Configuration

- [ ] Map decisive AcoustID evidence to immutable local-key recording expectations.
- [ ] Filter already-evaluated MusicBrainz candidates only after structural assignment.
- [ ] Preserve every existing structural score component, assignment, threshold, and gate.
- [ ] Treat unavailable, no-match, and ambiguous evidence as neutral.
- [ ] Allow the compatibility filter to remove incompatible runner-ups without adding score.
- [ ] Return `acoustid_recording_conflict` when decisive evidence rejects all candidates.
- [ ] Generate four-field findings only from the selected complete MusicBrainz release candidate.
- [ ] Prove AcoustID cannot rescue weak score, weak pair assignments, incomplete assignment, or ambiguous assignment.
- [ ] Integrate optional AcoustID evidence into existing-library `--identity` only.
- [ ] Never calculate missing fingerprints during `--identity`, including when `compute_missing=true`.
- [ ] Add `--acoustid` and `--fingerprint-missing` with frozen authority.
- [ ] Compose standalone mode safely with `--apply`, `--all`, and query selection.
- [ ] Reject every frozen invalid option combination before selection/backend/network work.
- [ ] Integrate the exact public `acoustid` configuration subtree via `AcoustIDSettings.from_mapping()`.
- [ ] Preserve lazy backend, environment, and network boundaries.
- [ ] Keep importer/acoustid autotagger behavior unchanged and owned by native beets `chroma`.
- [ ] Cover Albums, singletons, repeated recordings, multidisc releases, bonus tracks, near ties, contradictory evidence, standalone preview/apply, CLI validation, and configuration validation.
- [ ] Pass final supported Python 3.10-3.14 and beets `>=2.12,<3` CI with no live service dependency.

## Packaging And Compatibility

- [x] Keep Stages 01-04 free of new AcoustID Python dependencies.
- [ ] Keep Stage 05/base installation free of unnecessary AcoustID dependencies.
- [ ] Build wheel/sdist and inspect dependency metadata/archive contents after the full feature is integrated.
- [ ] Clean-install base, Discogs, and AcoustID-capable variants as applicable.
- [ ] Test plugin discovery and command help from built artifacts.

## Documentation And Release Readiness

- [ ] Document AcoustID versus Chromaprint versus beets `chroma`.
- [ ] Document existing-value reuse, explicit calculation, credentials, privacy,
  preview, database apply, identity filtering, and no-file-write boundaries.
- [ ] Add command, configuration, evidence, field, compatibility, and troubleshooting coverage.
- [ ] Update README capability/install summaries without exceeding its limit.
- [ ] Replace `No user-facing changes yet` under `Unreleased` during release-readiness work.
- [ ] Update context and handoff after Stage 05 merge.
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
