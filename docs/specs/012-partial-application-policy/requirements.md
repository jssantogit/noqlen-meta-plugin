# Requirements - Safe Partial Application Policy

## Goal

Preserve strict selected-release application by default while allowing an explicit partial mode to
apply only the independently safe mapped subset.

## Requirements

- Accept only normalized `strict` and `partial` modes; reject invalid enabled configuration before
  provider work.
- Keep direct application calls strict by default.
- In strict mode, any review or blocker applies nothing.
- In partial mode, apply only mapped changes and truthfully report withheld reviews and blockers.
- Treat no eligible mapped changes as a valid no-op.
- Validate integrity, stale mapped state, all values, and unique targets before any mutation.
- Abort the entire mapped subset on every application contract failure.
- Invalidate selected-info caches after successful mutation and never invoke downstream beets APIs.

## Out Of Scope

Review acceptance, lossy mapping, per-field recovery, rollback, direct Item/Album mutation,
persistence, CLI, provider or resolver changes, and beets core changes.
