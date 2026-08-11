import subprocess
import sys

from beets.plugins import BeetsPlugin

from beetsplug.noqlenmeta import NoqlenMetaPlugin


def test_plugin_class_uses_beets_plugin_contract() -> None:
    assert issubclass(NoqlenMetaPlugin, BeetsPlugin)


def test_plugin_load_does_not_import_optional_discogs_client() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import beetsplug.noqlenmeta; "
            "assert 'beetsplug.noqlenmeta.providers.discogs' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_plugin_load_does_not_import_optional_librosa() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import beetsplug.noqlenmeta; assert 'librosa' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
