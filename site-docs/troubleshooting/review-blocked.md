# REVIEW and BLOCKED Results

`REVIEW` means useful evidence exists, but automatic confidence or safety is
insufficient. `BLOCKED` means a safety, identity, mapping, stale-state, or
contract requirement prevented the change.

Common causes include:

- conflicting current and proposed values while preservation is enabled;
- multiple provider values for a singular target;
- confidence below the configured threshold;
- missing or ambiguous identity;
- unsupported file mapping or filesystem guarantee;
- a source or database target changing after planning.

Read the reason in preview, correct the evidence, configuration, or target, and
preview again. Partial mode may retain independently safe ordinary fields, but
partial is not force. It never accepts a review, fabricates a mapping, lowers
identity gates, or bypasses stale checks. Noqlen has no force mode.

See [Strict and Partial](../concepts/strict-vs-partial.md) for the current
conceptual model.
