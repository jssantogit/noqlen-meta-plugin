# Preview, Apply and Write

## Preview

Preview is the default and non-mutating. It may collect provider evidence or
run configured local analysis, but writes no ordinary database metadata,
sidecars, or audio tags.

Preview results mean:

- `KEEP`: retain the current value;
- `PROPOSE`: a safe-enough prepared value exists, but preview changed nothing;
- `REVIEW`: useful evidence exists without sufficient automatic safety;
- `BLOCKED`: a safety, identity, mapping, stale-state, or contract rule stopped
  the change.

## Apply

Ordinary `--apply` authorizes approved database changes. Verified `cover.jpg`
sidecars may be written and `Album.artpath` persisted. Audio files remain
unchanged unless `--write` is also present.

Identity `--identity --apply` and AcoustID `--acoustid --apply` have separate,
fixed database authorities. They are not ordinary field application.

## Write

Ordinary file synchronization requires `--apply --write`. Provider collection
and analysis are already complete: adding `--write` never triggers another
provider call or analyzer expansion. Verified candidate copies are written,
reopened, and checked before source replacement.

`--identity-tags --write` is a separate four-MBID workflow. Native `beet write`
and importer `import.write` are beets controls, not aliases for Noqlen
`--write`. See [beets Interaction](../technical-reference/beets-interaction.md).
