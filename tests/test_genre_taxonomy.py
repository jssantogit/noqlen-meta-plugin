import hashlib
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from runpy import run_path
from typing import cast

from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)

_normalized_snapshot = cast(
    Callable[[bytes], bytes],
    run_path(str(Path(__file__).parents[1] / "scripts/update_genre_taxonomy.py"))[
        "_normalized_snapshot"
    ],
)


def test_taxonomy_recognizes_representative_specific_genres() -> None:
    expected = {
        "idm": "IDM",
        "edm": "EDM",
        "ebm": "EBM",
        "fm synthesis": "FM Synthesis",
        "glitch hop edm": "Glitch Hop EDM",
        "hard nrg": "Hard NRG",
        "hi-nrg": "Hi-NRG",
        "uk garage": "UK Garage",
        "us power metal": "US Power Metal",
        "mpb": "MPB",
        "opm": "OPM",
        "tbm": "TBM",
        "ytpmv": "YTPMV",
        "black midi": "Black MIDI",
        "children's music": "Children's Music",
        "ʻōteʻa": "ʻŌteʻa",
        "j-pop": "J-pop",
        "K-pop": "K-pop",
        "r&b": "R&B",
        "technical death metal": "Technical Death Metal",
        "progressive metal": "Progressive Metal",
        "melodic death metal": "Melodic Death Metal",
        "drum and bass": "Drum and Bass",
    }
    for value, canonical_name in expected.items():
        result = DEFAULT_GENRE_TAXONOMY.classify(value)
        assert result.category is GenreSemanticCategory.GENRE
        assert result.canonical_name == canonical_name


def test_taxonomy_updater_applies_deterministic_token_casing() -> None:
    raw_names = (
        "  idm  ",
        "edm",
        "ebm",
        "aor",
        "asmr",
        "eai",
        "fm synthesis",
        "glitch hop edm",
        "hard\t nrg",
        "hi-nrg",
        "nwobhm",
        "uk garage",
        "uk82",
        "us power metal",
        "mpb",
        "opm",
        "tbm",
        "ytpmv",
        "black midi",
        "children's music",
        "canzone d'autore",
        "black 'n' roll",
        "ʻōteʻa",
        "j-pop",
        "k-pop",
        "r&b",
        "technical death metal",
        "drum and bass",
    )

    snapshot = _normalized_snapshot("\n".join(raw_names).encode()).decode().splitlines()

    assert snapshot == [
        "AOR",
        "ASMR",
        "Black 'N' Roll",
        "Black MIDI",
        "Canzone D'Autore",
        "Children's Music",
        "Drum and Bass",
        "EAI",
        "EBM",
        "EDM",
        "FM Synthesis",
        "Glitch Hop EDM",
        "Hard NRG",
        "Hi-NRG",
        "IDM",
        "J-pop",
        "K-pop",
        "MPB",
        "NWOBHM",
        "OPM",
        "R&B",
        "TBM",
        "Technical Death Metal",
        "UK Garage",
        "UK82",
        "US Power Metal",
        "YTPMV",
        "ʻŌteʻa",
    ]


def test_aliases_collapse_to_one_canonical_identity() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    assert taxonomy.classify("kpop").canonical_name == taxonomy.classify("K-Pop").canonical_name
    assert taxonomy.classify("rnb").canonical_name == taxonomy.classify("R&B").canonical_name
    assert taxonomy.classify("dnb").canonical_name == taxonomy.classify(
        "drum and bass"
    ).canonical_name


def test_classifier_separates_non_genre_semantics() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    assert taxonomy.classify("Energetic").category is GenreSemanticCategory.MOOD
    assert taxonomy.classify("Korean").category is GenreSemanticCategory.ORIGIN
    assert taxonomy.classify("Girl Group").category is GenreSemanticCategory.DESCRIPTOR
    assert taxonomy.classify("2024").category is GenreSemanticCategory.NOISE
    assert taxonomy.classify("Spotify").category is GenreSemanticCategory.NOISE
    assert (
        taxonomy.classify("Synthetic Artist", artist_names=("Synthetic Artist",)).category
        is GenreSemanticCategory.NOISE
    )


def test_broad_categories_are_explicit_not_inferred() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    for value in ("Rock", "Pop", "Metal", "Electronic"):
        assert taxonomy.classify(value).broad is True
    for value in ("Technical Death Metal", "K-pop", "Drum and Bass"):
        assert taxonomy.classify(value).broad is False


def test_structural_and_community_noise_is_rejected() -> None:
    taxonomy = DEFAULT_GENRE_TAXONOMY
    for value in (
        "90s",
        "albums I own",
        "seen live",
        "last.fm",
        "track",
        "female vocalists",
        "this is a very long personal tagging phrase",
    ):
        assert taxonomy.classify(value).category is GenreSemanticCategory.NOISE


def test_packaged_snapshot_is_available_through_importlib_resources() -> None:
    package = "beetsplug.noqlenmeta.genre_taxonomy"
    data = resources.files(package).joinpath("genres.txt").read_bytes()
    assert data
    assert len(DEFAULT_GENRE_TAXONOMY.snapshot_id) == 16
    expected = hashlib.sha256(data).hexdigest()[:16]
    assert DEFAULT_GENRE_TAXONOMY.snapshot_id == expected
