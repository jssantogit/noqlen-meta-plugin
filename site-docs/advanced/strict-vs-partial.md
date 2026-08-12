# Strict vs Partial

**Strict** means one ordinary `REVIEW` or mapping blocker withholds all ordinary
Noqlen changes for that target.

**Partial** means independently safe, losslessly mapped ordinary fields may
apply while review and blocked fields remain unchanged.

```text
genres -> safe proposal
styles -> safe proposal
year -> REVIEW

--apply -> strict: apply none for the target
--apply --partial -> apply genres/styles; preserve year
```

Partial is not force. It does not accept `REVIEW`, choose ambiguity, lower
confidence, discard a blocked value, bypass stale-state checks, repair identity
partially, or apply file tags partially. Noqlen has no force mode.

Library commands request `--partial` explicitly. Importer enrichment uses
`apply_mode: partial`; that setting does not control `beet nm`. Identity,
AcoustID application units, and identity-tag synchronization retain their own
coherent boundaries.
