# Review - iTunes Album Enrichment and Multi-Provider Resolution

## Scope review

- [x] `ITunesProvider` satisfies the existing provider protocol without domain redesign.
- [x] Every path resolves one concrete collection before candidate emission.
- [x] Direct identity, UPC lookup, and bounded text search are conservative and deterministic.
- [x] Only genres and year are emitted; store country and unsupported metadata are ignored.
- [x] Discogs and iTunes can contribute to one resolver pass with isolated failures.
- [x] Existing Field Authority outranks cross-provider confidence.
- [x] Provider gating avoids calls that cannot affect enabled fields.
- [x] Preview decisions remain read-only and display `iTunes` correctly.
- [x] Default tests are fixture-backed and the live smoke is explicitly opt-in.

## Validation evidence

- Focused iTunes and integration tests: `80 passed` after review hardening.
- `ruff check .`: passed.
- `pytest`: `170 passed`, with live tests skipped by default.
- `python scripts/check_repo_contamination.py`: passed.
- `git diff --check`: passed.
- `NOQLEN_LIVE_TESTS=1 pytest -m live`: `2 passed` against the public Discogs and iTunes
  services.

## Residual risks

- Public catalog availability and storefront responses can change independently of Noqlen.
- UPC coverage varies by storefront; conservative no-result behavior can omit enrichment rather than
  risk selecting the wrong collection.
- Provider-local confidence is not a universal quality score and intentionally cannot override Field
  Authority.

## Final status

Complete. Baseline and opt-in live validation are green, and the scoped diff is ready for the
requested Block 007 commit.
