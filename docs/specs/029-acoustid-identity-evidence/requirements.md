# Block 029 Requirements

## Goal

Add conservative AcoustID/Chromaprint evidence to Noqlen Meta so existing
library tracks can be fingerprinted or looked up explicitly, AcoustID identifiers
can be reviewed and stored in the beets database, and decisive recording-level
evidence can strengthen the existing MusicBrainz identity audit without
bypassing its structural safety rules.

The intended release family is Noqlen Meta 1.1.0. Block 029 planning does not
change the package version, dependencies, public commands, or product behavior.

## Product Positioning

- Keep beets as matcher, importer, library manager, and owner of native tag
  synchronization.
- Do not create a second autotagger or duplicate the beets `chroma` plugin.
- Treat AcoustID as an identity-evidence subsystem, not as an ordinary album
  metadata provider.
- Keep ordinary enrichment, AcoustID evidence, MusicBrainz identity repair, and
  file writing behind separate authority boundaries.
- Preserve preview-first and fail-closed behavior.

## Initial Scope

- Support existing-library Albums and singletons selected through normal beets
  queries.
- Add a dedicated AcoustID preview mode, provisionally
  `beet nm --acoustid QUERY`.
- Let `--apply` in that mode store only supported AcoustID fields in the beets
  database after stale-state verification.
- Support explicit missing-fingerprint generation; never compute fingerprints
  during ordinary enrichment or an unrelated identity command by default.
- Reuse valid existing beets `acoustid_id` and `acoustid_fingerprint` values
  before invoking a local backend or the network.
- Allow the existing `--identity` audit to consume decisive AcoustID recording
  evidence when the AcoustID subsystem is explicitly enabled.
- Defer importer fingerprint generation and AcoustID-based autotagger candidate
  creation. The native beets `chroma` plugin remains the importer integration
  for those behaviors.

## Identity Authority

- AcoustID may identify one or more MusicBrainz recording MBIDs for a local
  audio fingerprint.
- AcoustID must not directly select or write a MusicBrainz release MBID,
  release-group MBID, or release-track MBID.
- AcoustID must not infer occurrence-specific identity by choosing the first
  release, medium, or track returned by a recording payload.
- A complete four-field MusicBrainz identity must still originate from a
  complete `MusicBrainzReleaseIdentity` candidate acquired through the existing
  MusicBrainz source.
- Decisive AcoustID recording evidence may reject an incompatible MusicBrainz
  release candidate or confirm assignment compatibility.
- AcoustID evidence must not add score points that rescue a structurally weak
  MusicBrainz candidate.
- Existing structural score, pair-score, complete-assignment, and unique-margin
  requirements remain mandatory.
- When decisive evidence rejects every otherwise eligible candidate, identity
  remains ambiguous and is not repair-ready.
- Ambiguous or unavailable AcoustID evidence leaves the structural MusicBrainz
  audit unchanged; it never becomes negative evidence merely because lookup is
  unavailable.

## Evidence Selection

- Preserve all bounded AcoustID result groups needed to evaluate ambiguity.
- Validate response shape, identifiers, scores, recording lists, and limits
  before constructing domain values.
- Require an explicit minimum AcoustID score.
- Require a minimum margin between competing result groups or recording
  identities before evidence is decisive.
- Require exactly one canonical recording MBID after bounded aggregation for a
  decisive track verdict.
- Treat multiple plausible recording MBIDs, near ties, malformed identifiers,
  and conflicting high-scoring groups as review/ambiguous outcomes.
- Use local title, artist, and duration only as corroborating or veto evidence;
  they cannot manufacture a recording identity absent from AcoustID.
- Keep thresholds finite, bounded, validated, and covered by boundary tests.

## Fingerprint Acquisition

- Prefer a valid existing beets fingerprint.
- Compute a missing fingerprint only when the user explicitly requests it or a
  dedicated AcoustID setting explicitly permits it for that mode.
- Use a bounded local Chromaprint backend, initially `fpcalc` or a narrow
  compatible wrapper chosen during implementation.
- Do not require a fingerprint backend when every selected item already has a
  valid stored fingerprint.
- Apply a timeout and output-size limit to every backend invocation.
- Reject missing, malformed, oversized, or non-text fingerprint output.
- Capture a path-free file snapshot for generated fingerprints and verify the
  source file has not changed before storing derived database values.
- Never print a full fingerprint, raw backend output, or private file path.

## AcoustID Service Boundary

- Use the official HTTPS lookup endpoint.
- Send long fingerprints through a bounded POST request rather than placing the
  complete fingerprint in a displayed or logged URL.
- Require an application client key from a dedicated environment variable.
- Never print, persist, commit, or include the client key in diagnostics.
- Respect the service request-rate ceiling with sequential pacing.
- Bound timeout, response bytes, result count, recording count, retries, and
  cache size.
- Use a process-local bounded cache only; no persistent raw response cache.
- Convert network, timeout, rate-limit, and service failures into sanitized
  unavailable results that do not break unrelated workflows.
- Do not submit fingerprints or user data to AcoustID in Block 029.

## Database And File Boundaries

- AcoustID preview writes nothing.
- AcoustID `--apply` may change only the approved beets database fields for the
  selected Items.
- No AcoustID mode writes audio files directly.
- No force option is added.
- Existing non-empty AcoustID values are preserved by default.
- Conflicting existing values require review and block replacement.
- Application must plan all selected targets before the first database change.
- Application must re-fetch and verify exact database and generated-file
  snapshots before the first mutation.
- A stale target, membership change, path change, source-file change, or
  conflicting current value blocks the complete selected application unit.
- Native beets behavior remains responsible for any later generic database-to-
  file synchronization.

## Configuration And Credentials

- AcoustID is disabled by default.
- Missing or invalid AcoustID settings fail before backend or network work.
- Configuration must distinguish existing-value reuse, missing-fingerprint
  calculation, lookup enablement, identity-evidence use, score threshold,
  ambiguity margin, candidate bound, timeout, request pacing, and backend path.
- The API client key is supplied through `NOQLENMETA_ACOUSTID_API_KEY`; it is not
  a committed example value.
- Any optional Python dependency remains isolated in an `acoustid` extra and
  must preserve Python 3.10-3.14 and beets `>=2.12,<3` compatibility.
- Exact dependency bounds are selected only after clean-install and supported-
  Python validation.

## Output And Privacy

- Preview distinguishes reused fingerprint, generated fingerprint, lookup
  unavailable, no match, ambiguous evidence, decisive evidence, conflict, and
  planned database changes.
- Public output may display a shortened AcoustID ID and canonical recording
  MBID when useful.
- Public output never displays a full fingerprint, client key, raw response,
  backend command containing a private path, or provider exception text.
- Debug output remains sanitized and bounded.
- Reports and tests use synthetic identifiers and generated audio fixtures only.

## Testing

- Normal tests are offline and inject fake backend and service boundaries.
- Add domain, validation, score, margin, ambiguity, malformed-response, pacing,
  timeout, size-limit, cache, and sanitization tests.
- Add tests proving an existing fingerprint avoids backend discovery and
  execution.
- Add tests proving missing backend or key is non-fatal and accurately reported.
- Add tests proving AcoustID cannot directly produce release, release-group, or
  release-track writes.
- Add identity tests proving decisive recording evidence filters incompatible
  MusicBrainz candidates without changing structural scores.
- Add stale-database and stale-source-file application tests.
- Add package-extra and clean-install tests across the claimed Python matrix.
- Keep real AcoustID tests opt-in under the existing `live` marker and never
  require them for normal CI.

## Documentation And Release

- Document installation of the optional backend/dependency, API-key setup,
  privacy boundary, preview/apply behavior, beets `chroma` coexistence, and
  troubleshooting.
- Update complete public configuration and command references with automated
  drift checks.
- Record user-facing work under `CHANGELOG.md` `Unreleased` during
  implementation.
- Do not bump the package version or create a tag until implementation,
  documentation, compatibility, package, and release review gates pass.
