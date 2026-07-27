# Design - Safe Partial Library Database Application

## Flow

```text
validate CLI permission
  -> plan every selected Album
  -> reconstruct each canonical LibraryTargetPlan
  -> strict: block on withheld fields
  -> partial: classify withheld fields out
  -> guard dirty state and fetch fresh Album
  -> validate all mapped before-state, values, and targets
  -> mutate mapped fields together
  -> Album.store(inherit=True) once when mapped changes exist
```

`LibraryApplicationMode` is independent from importer `BeetsApplicationMode`. The application result
reports mode, applied changes, withheld counts, and successful storage. Partial mode changes only the
policy gate; mapping, stale-state safety, materialization, persistence, and command ordering remain
unchanged.
