"""Noqlen Meta beets plugin.

The package is intentionally minimal during the project-foundation block.
Metadata providers and enrichment behavior belong to later scoped blocks.
"""

from beets.plugins import BeetsPlugin


class NoqlenMetaPlugin(BeetsPlugin):
    """Entry point loaded by beets as the ``noqlenmeta`` plugin."""

    pass
