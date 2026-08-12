# Noqlen Meta V3 Wave 1A Release Catalog Plan

## Goal and boundary

Implement an internal, testable Release/Release Group catalog pipeline for
`date`, `original_date`, derived `original_year`, `release_type`,
`release_secondary_types`, `release_status`, and `edition`:

```text
provider evidence -> field authority -> resolution -> ChangePlan -> target plan
```

The normal V2 command/importer paths remain unchanged. Wave 1A adds no public
configuration, CLI option, file tag, release, identity behavior, AcoustID
behavior, or Wave 1B field.

## Architecture decisions

1. Keep `MetadataValue`, `MetadataCandidate`, `resolve_metadata()` and existing
   provider `supported_fields` as exact V2 compatibility surfaces.
2. Put canonical release catalog values and common date/type normalization in a
   dependency-light `release_catalog.py` module. `PartialDate` remains the
   foundation primitive.
3. Add explicit V3 evidence methods to existing provider adapters. These methods
   are called only by tests or a small internal Wave 1 service, never by normal
   V2 orchestration in this slice.
4. Register V3 provider capabilities separately from V2 `ProviderSpec` views.
   Authority rows may reference either implemented capability registry, while
   V2 caller checks retain exact current `supported_fields`.
5. MusicBrainz release evidence reuses `MusicBrainzSemanticClient.lookup_release`
   and its command cache. Exact Release Group lookup is added to that client as
   one narrow injected boundary and command-cache entity; no search is allowed.
6. Discogs and iTunes factor their existing acquisition result internally so V2
   candidates and V3 evidence can consume one concrete response per invocation.
   No endpoint or request count is added.
7. Add a focused release catalog resolver for `EXCLUSIVE` and `MULTIVALUE` only.
   Identity, taxonomy, lyrics, artwork and audio resolvers remain separate.
8. Generalize the existing ChangePlan source/value typing just enough for V2
   `FieldDecision` and V3 catalog decisions. Do not create `V3ChangePlan`.
9. Add a separate release catalog target planner. Existing V2 AlbumInfo/library
   mappers remain behaviorally unchanged. The new planner may emit multiple
   target components for one canonical date change and typed DB targets where
   native representation is semantically insufficient.
10. `date.year` and `original_date.year` are the only accepted sources for their
    compatibility projections in V3 plans. Providers never emit V3 `year` or
    `original_year` evidence.

## TDD execution

### 1. Canonical values and date semantics

Write failing tests for:

- `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-??-??`, `YYYY-MM-??`;
- impossible and malformed dates;
- compatibility and precision enrichment;
- controlled MusicBrainz primary/secondary type and release-status enums;
- controlled Discogs edition designations and rejection of remaster/reissue or
  arbitrary text.

Implement minimal parsers, compatibility comparison, most-precise compatible
selection, and deterministic projection helpers.

### 2. Provider evidence

Write provider-specific failing tests before production changes.

MusicBrainz:

- release date/status from exact cached Release payload;
- nested Release Group reuse;
- exact Release Group lookup only for requested missing fields;
- one lookup reused across all requested RG fields;
- malformed/mismatched/supporting failure isolation;
- zero RG calls when no RG field is requested;
- V2 includes, output and call counts unchanged.

Discogs:

- structural `released` date;
- controlled whole-value/structured edition descriptors;
- conflict represented as multiple evidence for resolver REVIEW;
- no title/notes/remaster/reissue inference;
- one concrete release request total.

iTunes:

- valid `releaseDate` to `PartialDate`;
- malformed/missing date omitted;
- exact same lookup/search request behavior as V2.

Add only small sanitized fixture fields needed by these parsers.

### 3. Capability and authority

After provider methods exist, add only implemented V3 capabilities:

- MusicBrainz: date, original_date, release_type,
  release_secondary_types, release_status;
- Discogs: date, edition;
- iTunes: date.

Add authority rows matching the approved 030 proposal. Keep `original_year`
without provider capability or independent authority. Extend consistency tests
to validate both V2 and V3 capability registries.

### 4. Release catalog resolution

Write failing tests for:

- primary, secondary and fallback eligibility;
- corroboration-only/ineligible exclusion;
- compatible date precision coalescing;
- material primary/secondary conflict REVIEW;
- conservative existing-value precision behavior;
- deterministic evidence order;
- multivalue union only for identical field/entity scope;
- provider absence producing no deletion;
- derived year/original_year consistency.

Implement immutable catalog decisions with semantic actions compatible with
ChangePlan. Do not modify the V2 resolver algorithm.

### 5. ChangePlan bridge and targets

Write failing tests that prove one ChangePlan can retain either V2 candidate or
V3 evidence provenance. Generalize source/value contracts without changing V2
construction or equality behavior.

Write target tests for:

- exact known date components only;
- compatible more-precise current target preservation;
- original date components;
- albumtype and albumstatus native mappings;
- separate typed DB `release_secondary_types` and deterministic native
  `albumtypes` projection only with primary type;
- typed DB-only edition;
- no edition file target/private tag.

Register only Album flexible DB types required by Wave 1A: `edition` and
`release_secondary_types`.

### 6. Documentation and verification

Add `docs/specs/031-v3-release-catalog/implementation-contract.md` covering
fields, evidence, authority, precision, type/edition rules, targets and
deferrals. Do not update public user documentation.

Run focused tests after every stage, then:

```text
pytest
ruff check .
python scripts/check_public_docs.py
python scripts/check_repo_contamination.py
mkdocs build --strict
git diff --check
```

Run the GitHub compatibility subset in coherent beets 2.12.0 and latest beets
2.x environments. Review the final diff for provider search/call expansion,
premature public wiring, date/year inconsistency, edition guessing, private
tags, identity/AcoustID changes, Wave 1B scope, TODO/TBD and sensitive data.

## Commit sequence

1. Plan and canonical release catalog semantics.
2. MusicBrainz V3 release catalog evidence.
3. Discogs and iTunes V3 release catalog evidence.
4. V3 capabilities, authority and catalog resolution.
5. ChangePlan bridge, target planning and typed DB fields.
6. Internal implementation contract and final consistency tests.

Stage only named files. Do not merge, tag, release or publish.
