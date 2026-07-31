# Result Statuses

You will be able to read an ordinary preview without seeing protected values
such as raw lyrics, malformed identifiers, or private paths.

| Status | Meaning | Next step |
| --- | --- | --- |
| `KEEP` | The current value remains. | No action is needed. |
| `PROPOSE` | A safe change is available. | Review the source and value. |
| `REVIEW` | A conflict or evidence needs attention. | Adjust policy or keep the existing value. |
| `BLOCKED` | The target cannot represent or apply the change safely. | Read the reason and mapping limits. |

Example synthetic preview:

```text
Noqlen Meta / library target preview:
  application: disabled (preview only)
  file tags: unchanged

  genres
    PROPOSE
    proposed: Electronic, Ambient
    source: Discogs

  country
    KEEP
    current: GB

  year
    REVIEW
    current and candidate values conflict

  media
    BLOCKED
    persistent Album has no supported album-level media target
```

Identity previews use more specific verdicts because all four IDs must form a
coherent target. Identity-tag previews describe each file independently but do
not display the path. See [Troubleshooting](../troubleshooting/index.md) when a
status prevents the intended action.
