# Noqlen Meta V3 Wave 1B Recording/Work and Wave 1 Integration Plan

## Goal and boundary

Complete Wave 1 by integrating the internal Wave 1A release catalog pipeline
with new Recording/Work identifier enrichment:

```text
shared provider acquisition -> V2 candidates and V3 evidence
-> domain resolution -> one ChangePlan per Release or Track
-> importer/library targets -> preview -> apply -> optional verified write
```

The implementation covers `date`, `original_date`, `release_type`,
`release_secondary_types`, `release_status`, `edition`, plural `isrcs`,
Recording-to-Work `works`, Work-scoped plural `iswcs`, and structurally proven
`recording_date`. It adds no Wave 2 credits, aliases, versions, languages,
explicitness, artwork, audio fields or identity repair. AcoustID remains a
separate compatibility subsystem and never supplies or writes MusicBrainz IDs.

## Architecture decisions

1. Define a runtime-domain-neutral `PlannableDecision` protocol in
   `changeplan.py`. V2, release-catalog and recording-identity decisions expose
   `resolved_value`, `selected_source`, and only real `contributing_evidence`.
   Keep compatibility wrappers only where existing callers need them.
2. Use one ChangePlan builder and one checked composition function. Duplicate
   canonical fields are rejected unless the integration explicitly suppresses
   legacy V2 `year` while V3 `date` is enabled. There is no last-write-wins.
3. Correct release-catalog ordering to use authority role before deterministic
   source tie-breaks. Primary provenance wins equivalent values; a compatible
   secondary may supply additional date precision while retaining the primary
   as a contributor. Fallback participates only without eligible primary or
   secondary evidence.
4. Add immutable `WorkReference` as the only structured Work value accepted by
   `MetadataEvidence`. It validates canonical Work UUIDs, non-empty optional
   titles, relation identity, attributes and ordering, and is represented as a
   typed tuple in the closed canonical value vocabulary.
5. Extend the retained MusicBrainz track provider with one enrichment boundary
   that computes a requested include union and reuses `CommandEntityCache`.
   Exact Recording MBID is the sole gate. Recording and Work lookups never
   search, use ISRC/title matching, or invoke AcoustID.
6. Parse plural ISRC from the exact Recording, structured Recording-to-Work
   relationships, and all valid ISWCs from exact related Work lookups. Preserve
   Work scope on ISWC evidence. Supporting Work failures do not discard ISRC,
   Work identity or successful sibling Work evidence.
7. Emit `recording_date` only from audited recording relationships whose begin
   and end represent the same safe `PartialDate`. Never use Recording
   `first_release_date`, release dates, names or inferred event/place dates.
8. Add a focused recording-identity resolver for identifier-set enrichment,
   Work identity and exclusive recording date. Existing valid supersets are
   retained; omissions never delete; partial overlap/material disagreement is
   REVIEW; Work comparison is primarily by MBID.
9. Add narrow shared release enrichment results to MusicBrainz, Discogs and
   iTunes. One acquired Release/collection produces both V2 candidates and V3
   evidence. MusicBrainz may perform at most one exact Release Group support
   lookup when requested missing fields require it.
10. Gate V3 provider contribution independently through enabled fields,
    provider state, `ProviderCapability`, scope and identity prerequisites.
    Do not reinterpret V2 ordinal authority configuration as V3 roles.
11. Read Wave 1 current state into canonical values from selected metadata and
    persisted models. Malformed stored values are ignored. Release contexts
    retain only canonical established Release Group IDs as exact acquisition
    anchors, never as identity-repair evidence.
12. Project one unified Release or Track ChangePlan into the existing importer
    and library target universes. Mapping remains pure. Release-type combined
    projection uses effective accepted primary and secondary state, including
    KEEP/PROPOSE combinations, without manufacturing canonical changes.
13. Persist queryable plural Item fields `isrcs`, `iswcs`, `mb_workids` as
    `MULTI_VALUE_DSV` and `recording_date` as canonical ISO partial-date text.
    Scalar native ISRC/Work projections occur only for exactly one value; no
    arbitrary first value or parallel work-title list is created.
14. Generalize file projection so one canonical change may produce multiple
    native MediaFile changes. Write only audited lossless targets. Multiple
    ISRCs/Works and DB-only ISWC, recording date and edition remain blocked for
    file sync without blocking safe database application under partial mode.
    Preserve the existing candidate-copy, verification, atomic replacement,
    recovery and stale-state machinery.
15. Importer enrichment consumes only the selected AlbumInfo/TrackInfo exact
    identities after `Action.APPLY`; beets remains matcher and persistence/file
    authority. Existing-library preview/apply/write uses one acquired and
    resolved plan with no provider work between planning and write.
16. Add Wave 1 fields to production defaults and derive public documentation
    from those defaults. `date=true` suppresses V2 provider year competition and
    derives year from the accepted date; `date=false, year=true` preserves exact
    V2 behavior.

## TDD execution

### 1. Shared planning and authority

Write failing tests for:

- byte-for-byte equivalent V2 ChangePlan values and ordering;
- one generic builder accepting V2 and V3 decision structures;
- release/recording resolver modules absent from `changeplan.py` runtime imports;
- selected source plus real contributors only;
- low-confidence/ineligible/alternative evidence never becoming contributors;
- checked ChangePlan composition and duplicate-field rejection;
- primary selected provenance for equivalent primary/secondary evidence;
- secondary precision enrichment retaining primary corroboration;
- fallback suppression and material-conflict REVIEW;
- effective release type projection for both KEEP/PROPOSE directions.

Implement the protocol properties on all decision classes, authority-aware
ordering and target effective-state input. Run the focused planning, resolution
and release mapping tests before committing.

### 2. Work model and canonical evidence

Write failing tests for canonical UUID/title/relation validation,
deterministic relation deduplication and ordering, preserved attributes and
ordering keys, and rejection of arbitrary object tuples in evidence. Implement
`work_identity.py` and the closed `CanonicalValue` extension without parsing
Wave 2 semantics from attributes.

### 3. Exact MusicBrainz Recording/Work acquisition

Add small sanitized Recording and Work fixtures or focused synthetic payloads.
Write failing provider tests for:

- no Recording MBID means no request;
- one Recording request for simultaneous semantic and Wave 1 output;
- requested include union and zero Work lookup for ISRC-only enrichment;
- plural valid deduplicated ISRC extraction;
- deterministic Recording-to-Work relation extraction without title matching;
- one exact lookup per Work and all valid ISWCs scoped to that Work;
- missing/failed one Work preserves ISRC, Work identity and sibling output;
- safe same begin/end recording relation date only;
- explicit rejection of `first_release_date`, intervals and one-sided dates;
- provider response/relation order independence and duplicate stability.

Implement only the includes and relationship parsing required by Wave 1.

### 4. Recording identity resolution

Write failing tests for empty/current-equal/subset/superset/partial-overlap/
disjoint identifier sets, malformed existing data, multiple Works, same-MBID
different-title compatibility, Work conflict, multiple recording dates, and
provider failure as no evidence. Implement immutable decisions satisfying the
shared planning protocol and field-specific authority rules.

### 5. Shared release acquisition and public contribution gates

Write request-counting tests proving combined V2/V3 acquisition uses:

- one Discogs concrete Release;
- one iTunes collection acquisition path;
- one MusicBrainz Release response plus at most one required exact Release
  Group support response.

Add the smallest provider enrichment result boundary. Add V3 capabilities and
tests proving enabled capable fields trigger normal processing, while disabled
or non-executable fields trigger no calls. Test `date`/legacy `year`
coexistence in both configurations.

### 6. Unified importer and library planning

Extend context/current-state tests for all Wave 1 release and track fields,
canonical partial-date round trips, legacy scalar/semicolon ISRC fallback,
plural IDs, Work compatibility, and release-group anchors. Compose V2,
semantic, BPM and V3 decisions into one immutable plan before strict/partial
policy. Test selected importer exact identities, ordinary library preview,
strict apply, partial apply, second-run no-op and optional-provider failure
isolation.

### 7. DB and file targets

Register typed Item fields and add pure mapping tests for every plural/scalar
projection and blocker. Extend real temporary-library tests for persistence and
round trips. Refactor file projection tests to cover date component expansion,
original date, supported release type/status, one ISRC, multiple-ISRC blocker,
single Work only where audited MediaFile targets exist, and DB-only blockers.
Keep existing cross-format safety and stale-state tests green.

### 8. Preview and public documentation

Generalize source rendering for `MetadataCandidate` and `MetadataEvidence`,
optional confidence, entity/scope, reason, REVIEW/BLOCKED and concise
corroboration. Do not expose oversized payload data, paths or secrets.

Update production defaults, exact full configuration examples, configuration,
field/provider and workflow documentation. Clearly distinguish release,
original and recording dates; ISRC, Work and ISWC; plural DB persistence;
DB-only fields; file limitations; preview/apply/write; and upcoming V3 status.
Create the 032 implementation contract and amend 031 only where final public
integration supersedes its internal-only statements.

## Commit sequence

1. Plan.
2. Generic ChangePlan contract and authority corrections.
3. Work identity and typed canonical evidence.
4. MusicBrainz Recording/Work acquisition.
5. Recording identifier resolution.
6. Shared release acquisition and capability/config gates.
7. Unified importer/library planning and current-state reads.
8. DB and file target projection/application.
9. Preview and public documentation contracts.
10. Final regression fixes and verification evidence.

Each commit stages named files only. Do not merge, tag, release, publish, alter
the package version, create private audio tags, or begin Wave 2.

## Final verification

Run focused red/green tests throughout, then:

```text
pytest
ruff check .
python scripts/check_public_docs.py
python scripts/check_repo_contamination.py
mkdocs build --strict
git diff --check
```

Confirm the GitHub workflows still cover Python 3.10 through 3.14,
`beets==2.12.0`, latest `beets<3`, package, documentation and audio-analysis.
Review the final diff and searches for MusicBrainz search, AcoustID ordinary
usage, `first_release_date` recording-date promotion, arbitrary first ISRC/Work,
plural loss, duplicate provider/entity requests, V2 year competition,
domain-specific ChangePlan imports, false contributors, private tags, primary
artist/title rewrites, Wave 2 scope, released-V3 claims, TODO/TBD, secrets and
private user data or paths.
