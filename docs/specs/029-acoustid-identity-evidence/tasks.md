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
- [x] Validate every boolean, integer, finite-number, threshold, timeout, rate,
  count, cache, and non-empty `fpcalc` setting.
- [x] Keep the client key outside settings and avoid environment access.
- [ ] Add `AcoustIDTargetResult` only in the workflow stage that owns exact
  database snapshots and plans.
- [ ] Integrate the AcoustID subtree into public plugin defaults only with the
  later command/public-configuration stage.
- [ ] Add dedicated `--acoustid` / `--fingerprint-missing` authority only in the
  later command stage.
- [ ] Reject unsafe public-mode combinations before target selection in that
  command stage.

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

## Next Stage: Preview, Mapping, And Database Application

- [ ] Define and review the Stage 04 workflow brief before product
  implementation begins.
- [ ] Decide the smallest safe Stage 04 boundary between standalone preview,
  database planning, and application without pulling command or MusicBrainz
  integration into scope.
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
  source-file, or current-value changes.
- [ ] Store only planned Item database fields.
- [ ] Prove AcoustID mode never writes audio files or MusicBrainz fields.
- [ ] Add success, no-op, conflict, stale-state, and rollback-before-first-write
  workflow tests.

## Future Stage: MusicBrainz Identity Integration

- [ ] Add pure mapping from decisive AcoustID evidence to local-key recording
  expectations.
- [ ] Add immutable candidate-compatibility result separate from structural
  score values.
- [ ] Filter structurally evaluated MusicBrainz release candidates only after
  existing assignments are calculated.
- [ ] Preserve every existing score component and threshold unchanged.
- [ ] Treat unavailable, no-match, and ambiguous evidence as neutral.
- [ ] Return `acoustid_recording_conflict` when decisive evidence rejects every
  candidate.
- [ ] Generate four-field findings only from the selected complete MusicBrainz
  release candidate.
- [ ] Prove AcoustID cannot rescue weak structure, weak pair assignments,
  incomplete assignment, or insufficient margin.
- [ ] Cover Albums, singletons, repeated recordings, multidisc releases, bonus
  tracks, near ties, and contradictory evidence.

## Future Stage: Command And Public Configuration

- [ ] Add `--acoustid` and `--fingerprint-missing` with frozen authority.
- [ ] Compose safely with `--apply` and `--all`.
- [ ] Reject frozen invalid option combinations before selection/local work.
- [ ] Integrate the exact AcoustID subtree into `configuration.default_config()`.
- [ ] Update command, configuration, and documentation drift checks.
- [ ] Keep preview as the default and application database-only.

## Packaging And Compatibility

- [x] Keep Stages 01-03 free of new AcoustID Python dependencies.
- [ ] Keep base installation free of unnecessary AcoustID dependencies.
- [ ] Test Python 3.10-3.14 and beets `>=2.12,<3` boundaries for the complete
  integrated feature before release.
- [ ] Build wheel/sdist and inspect dependency metadata/archive contents after
  the full feature is integrated.
- [ ] Clean-install base, Discogs, and AcoustID-capable variants as applicable.
- [ ] Test plugin discovery and command help from built artifacts.

## Documentation And Release Readiness

- [ ] Document AcoustID versus Chromaprint versus beets `chroma`.
- [ ] Document existing-value reuse, explicit calculation, credentials, privacy,
  preview, database apply, and no-file-write boundaries.
- [ ] Add command, configuration, evidence, field, compatibility, and
  troubleshooting coverage.
- [ ] Update README capability/install summaries without exceeding its limit.
- [ ] Replace `No user-facing changes yet` under `Unreleased` during public
  feature integration.
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
