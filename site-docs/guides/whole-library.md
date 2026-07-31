# Process The Whole Library

You will preview a bounded whole-library operation before granting writes.

`--all` means all targets in the selected mode:

```bash
beet nm --all
beet nm --identity --all
beet nm --identity-tags --all
```

Ordinary `--all` selects every Album. Identity and identity-tag `--all` select
every complete Album and every standalone singleton Item once.

Preview before any corresponding write:

```bash
beet nm --all
beet nm --apply --all
```

Network-provider time normally dominates ordinary enrichment. Identity-tag
mode performs no provider calls and processes files sequentially for safety.
All targets are planned before the first write, but database targets and files
commit independently rather than as one command-wide transaction.

Use a query instead of `--all` while learning the workflow. A query and
`--all` together are invalid.
