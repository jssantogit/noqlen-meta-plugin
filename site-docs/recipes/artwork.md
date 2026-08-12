# Add or Replace Album Covers

Configure the cover field and its source together:

```yaml
noqlenmeta:
  fields:
    cover: true
  providers:
    coverartarchive:
      enabled: true
  artwork:
    size: original
    replace_existing: false
```

Preview one identified album:

```bash
beet nm album:"Discovery"
```

With `replace_existing: false`, an existing `cover.jpg` or embedded image is
preserved. Change it to true only when the approved CAA front should replace
curated art.

`--apply` may create or replace verified `cover.jpg` sidecars and persist
`Album.artpath` without audio-file mutation. Multidisc albums receive the same
bytes in each real disc directory. `--apply --write` may additionally embed the
already prepared image; adding write does not cause another CAA lookup.
