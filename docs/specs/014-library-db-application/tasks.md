# Tasks - Strict Library Database Application

- [x] Add `--apply` to the existing `noqlenmeta`/`nm` Subcommand.
- [x] Add immutable prepared-plan and application-result representations.
- [x] Add strict plan integrity, clean Album, stale state, materialization, and uniqueness guards.
- [x] Persist mapped Album metadata through `Album.store(inherit=True)` only.
- [x] Split CLI execution into plan-all and apply-render phases.
- [x] Render truthful database and unchanged-file-tag status.
- [x] Add in-memory Album and Item persistence tests and forbidden-file-operation sentinels.
- [x] Add CLI permission, strict per-Album, planning-order, and store-failure tests.
- [x] Document the boundary in README, ADR 0010, specs, and context handoff.
- [x] Complete baseline validation and isolated command discovery.
- [ ] Commit and push the block branch.
