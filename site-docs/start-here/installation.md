# Installation

Install Noqlen Meta in the same Python environment as beets:

```bash
pip install beets-noqlenmeta
beet config -p
```

The second command prints the beets configuration file you need to edit. Enable
the plugin there:

```yaml
plugins:
  - noqlenmeta
```

Verify that beets can load the command:

```bash
beet nm --help
```

If this fails, see [Common Problems](../troubleshooting/index.md) or the exact
[compatibility contract](../technical-reference/compatibility.md).

Continue with [Basic Configuration](basic-configuration.md).
