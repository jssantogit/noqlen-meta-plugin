# Tasks - Strict Selected-Release Application

- [x] Add explicit default-off application configuration independent from preview.
- [x] Add immutable application result, strict gate, integrity checks, and stale-state checks.
- [x] Materialize validated target values and enforce unique fields before selected-info mutation.
- [x] Invalidate `AlbumInfo.raw_data` and `AlbumInfo.item_data` caches after mutation.
- [x] Integrate truthful preview and silent-preview safety logs without invoking downstream beets APIs.
- [x] Test all-or-nothing behavior, mutation scope, provider fallback, and normal beets handoff.
- [x] Document lifecycle, duplicate-resolution visibility, and downstream persistence effects.
- [x] Complete baseline validation and full scoped diff review.
- [ ] Commit and push the block branch.
