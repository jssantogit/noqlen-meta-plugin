# Block 029 Stage 05 / Implementation Completion Record

## Status

Stage 05 is complete and merged. Block 029 product implementation is complete.

There is no Stage 06.

```text
Stage 05 brief:        f78700846c531a99a02edd3102f3fba8f87c0f9f
Stage 05 PR:           #19
Final reviewed head:   9b76ff87b14440ddc576a0f0d84277ee8c8d5d23
Stage 05 main commit:  c5eabf80bbbe0f661aaa8867a78b3ebb83f0b3e3
Final CI:              run 74, success
```

This record changes no product behavior.

## Delivered

Stage 05 completed the remaining public and identity integration surface for AcoustID:

- decisive AcoustID recording evidence is converted to immutable local-key recording expectations;
- already-evaluated MusicBrainz release candidates are filtered for recording compatibility after structural assignment;
- AcoustID adds no structural score, changes no assignment, and relaxes no threshold or safety gate;
- unavailable, no-match, and ambiguous AcoustID evidence remain neutral;
- `acoustid_recording_conflict` blocks repair when decisive evidence rejects every candidate;
- existing-library `--identity` can reuse valid stored fingerprints and perform configured lookup, but never calculates a missing fingerprint;
- standalone `--acoustid` and `--fingerprint-missing` use the Stage 02-04 selection, fingerprint, lookup, planning, preview, stale-verification, and database-application boundaries;
- standalone `--apply` remains database-only and persists only `acoustid_id` / `acoustid_fingerprint` through the verified Stage 04 application unit;
- all standalone targets are planned and previewed before application;
- the exact frozen public `acoustid` configuration subtree is exposed through `AcoustIDSettings.from_mapping()`;
- invalid command combinations fail before target selection/backend/network work;
- native beets `chroma` remains responsible for importer acoustic matching and submission;
- no new AcoustID dependency, audio-file write authority, direct MusicBrainz write authority, version bump, tag, or publication was added.

## Reviewed Exceptions

The final product diff contained two reviewed scope exceptions that were accepted because they reduced drift rather than expanding authority:

1. `beetsplug/noqlenmeta/acoustid/library.py` exposes conversion from an already-selected library identity target to an AcoustID target, allowing `--identity` to reuse the same selection instead of performing a second library query.
2. Three public documentation files were updated in the product PR because the repository documentation drift gate required command/configuration parity.

Neither exception adds a new product boundary.

## Review Findings Resolved

External review found one Stage 05 behavior mismatch in the initial implementation: standalone application occurred before the prepared preview was rendered. Commit `1582afda18c13fd713201ee9c708ddd6016ed62f` changed the order to:

```text
plan all targets
-> render all prepared previews
-> when requested, apply the complete application unit
```

Regression coverage proves previews are emitted before both successful application and application failure.

The first PR CI run (#73) then failed during pytest collection on every Python version because `tests/acoustid/test_command.py` imported `tests.identity.helpers`, while `tests` is not an importable package in the clean CI environment. No product test had executed yet. Commit `9b76ff87b14440ddc576a0f0d84277ee8c8d5d23` replaced that cross-test import with the equivalent local UUID helper.

## Final Validation

CI run 74 passed on the exact reviewed head before squash merge:

- Python 3.10, 3.11, 3.12, 3.13, and 3.14: lint, full offline tests, and repository hygiene succeeded;
- beets minimum 2.12.0 compatibility succeeded;
- latest beets below 3 compatibility succeeded;
- public documentation contract and strict documentation build succeeded;
- package build, rendered metadata validation, archive inspection, and clean-install smoke test succeeded.

Normal CI requires no live AcoustID service, API key, real `fpcalc`, or audio-file write.

## Frozen Safety Outcome

Block 029 finishes with these boundaries intact:

- AcoustID is recording-level evidence, not a generic metadata provider;
- AcoustID never selects a release occurrence by itself;
- AcoustID never adds structural score or weakens MusicBrainz gates;
- AcoustID never writes MusicBrainz fields directly;
- standalone application writes only the two AcoustID database fields;
- `--identity` never calculates missing fingerprints;
- no Noqlen-owned importer fingerprint generation or autotagger candidate path was added;
- no audio-file writes or fingerprint submission were added;
- paths, fingerprints, API keys, backend output, and raw provider exceptions remain private.

## Remaining Work

Remaining work is release readiness only, not another implementation stage:

- synchronize project context/checklists and user-facing release notes;
- keep public command/configuration/troubleshooting documentation aligned;
- obtain green CI on the documentation-only completion PR;
- then decide the 1.1.0 version bump, tag, and publication separately.
