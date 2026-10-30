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

**A proposal and a blocker can appear together for the same album.**
This is not contradictory: `PROPOSE` describes a candidate field, whereas
`application: blocked` describes what was actually withheld for the target.

In ordinary **strict** mode, one review or mapping blocker prevents *all*
ordinary database changes for that target. The explicitly requested
`--apply --partial` mode can save only independent safe, losslessly
mapped ordinary fields; it cannot accept ambiguous or blocked values.

Read the reason in preview, correct the evidence, configuration, or target, and
preview again. Partial mode may retain independently safe ordinary fields, but
partial is not force. It never accepts a review, fabricates a mapping, lowers
identity gates, or bypasses stale checks. Noqlen has no force mode.

See [Strict vs Partial](../advanced/strict-vs-partial.md) for the current
conceptual model.
