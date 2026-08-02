# ADR 0024: v1 Documentation And Release Preparation

## Status

Accepted

## Context

The integrated plugin had a complete v1 product surface but its README mixed
user guidance, internal architecture, development history, and release state.
Package metadata remained pre-release, public documentation had no dedicated
platform, and release claims were not checked against production flags,
configuration defaults, packaging contents, or compatibility boundaries.

## Decision

1. The README is a short GitHub/PyPI landing page with a 500-line hard cap.
2. A public site is the canonical complete manual.
3. The public site uses MkDocs and Material for MkDocs.
4. Read the Docs is the intended host, subject to owner setup and verification.
5. Public source lives under `site-docs`; internal `docs/` is never the MkDocs source.
6. v1 public documentation is English and progressively beginner-first.
7. Tutorial, concepts, guides, reference, troubleshooting, advanced internals, and project information remain distinct.
8. Command and configuration reference is complete and checked against production.
9. Every write boundary is documented separately.
10. beets `import.write`, native `beet write`, and identity-tag `--write` are distinct.
11. Strict and partial behavior has a dedicated explanation.
12. Partial is never force and Noqlen v1 has no force mode.
13. Native beets skip/as-is and other non-apply decisions are respected.
14. Public documentation uses strict link, anchor, omitted-page, and navigation validation.
15. Documentation dependencies are pinned and shared by local, CI, and Read the Docs builds.
16. Analytics, tracking, and externally loaded custom fonts are disabled by default.
17. Package version becomes 1.0.0 with accurate positioning and only tested compatibility claims.
18. Build, Twine, wheel/sdist content, and clean-install smoke tests are release gates.
19. PyPI publication uses trusted publishing after the owner configures it.
20. No tag or upload occurs before reviewer PASS and merge to main.
21. The software license remains an explicit owner decision; no license metadata is invented.
22. No new provider or metadata feature enters v1 hardening.
23. Block 028 is the final development block.
24. Work stops after release preparation; external publication is an owner ceremony.
25. v1.0.0 package support is bounded to tested Python 3.10 through 3.14; Python 3.15 is not claimed.
26. Wheel and source `Requires-Python` equivalence is a semantic release gate.
27. A release tag must resolve to a commit contained in remote `main`; tag/version equality alone is insufficient.
28. Authenticated checkout fetches complete history without persisting credentials; ancestry is then verified locally and a missing `origin/main` fails closed.

## Consequences

Documentation drift becomes a CI failure when public flags or configuration
leaves are omitted. Internal ADR/spec/context material cannot be published by
the MkDocs configuration. The package can be built and audited without a live
Read the Docs project or PyPI publisher, while external publication remains
visibly gated.
