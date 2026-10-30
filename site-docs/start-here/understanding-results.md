# Understanding the Results

The preview groups each field under an operational status:

- **KEEP**: the current value is retained.
- **PROPOSE**: Noqlen prepared a value considered safe enough to propose, but
  preview changed nothing.
- **REVIEW**: useful evidence exists, but automatic confidence or safety is not
  sufficient.
- **BLOCKED**: a safety, identity, mapping, or contract requirement prevented
  the change.

**Check the final application status.** `PROPOSE` is a field-level
decision, not a guarantee that it will be saved. In ordinary **strict**
mode, one review or mapping blocker can withhold all ordinary changes
for that target. The preview shows `application: disabled (preview only)`
because nothing has been committed yet.

Do not treat `REVIEW` as an instruction to force a value. Noqlen has no force
mode. Adjust the evidence or configuration, then preview again.

For a concrete, beginner-oriented walkthrough, use the
[illustrative worked preview](reading-preview.md). For deeper semantics,
see [Preview, Apply and Write](../advanced/preview-apply-write.md).
When the proposals are acceptable, continue with
[Apply Your First Changes](apply-changes.md).
