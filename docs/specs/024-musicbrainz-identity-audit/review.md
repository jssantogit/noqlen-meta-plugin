# Block 024 Review

## Checklist

- Existing MBIDs never affect pair or release scores.
- Global assignment replaces positional mapping and supports reordered multidisc releases.
- Candidate IDs are complete canonical UUIDs with no double assignment.
- Scores, ordering, score thresholds, margins, and singleton strictness are deterministic.
- Weak, tied, malformed-source, duplicate-identity, and unmatched-local cases fail conservatively.
- Conflict supersedes missing and all four MBID categories are compared.
- Source acquisition uses beets facilities, is bounded and injectable, and exposes sanitized errors.
- Source bounding preserves exact-ID, primary-search, and singleton alternate-search inclusion order
  with first-occurrence deduplication; acquisition order never enters ranking.
- Production code performs no importer/CLI integration, mutation, persistence, or file operation.
- Forge concepts were reviewed, but its positional/write-coupled implementation was not copied.

## Validation

- Focused identity tests: 62 passed.
- Full offline suite: 862 passed, 5 opt-in live tests skipped.
- Ruff, repository contamination, and diff-whitespace checks: passed.
- Staged scope and diff review: passed.
