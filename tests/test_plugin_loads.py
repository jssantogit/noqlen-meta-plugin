from beets.plugins import BeetsPlugin

from beetsplug.noqlenmeta import NoqlenMetaPlugin


def test_plugin_class_uses_beets_plugin_contract() -> None:
    assert issubclass(NoqlenMetaPlugin, BeetsPlugin)
