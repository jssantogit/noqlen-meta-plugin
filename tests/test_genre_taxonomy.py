from importlib import resources

from beetsplug.noqlenmeta.genre_taxonomy import (
    DEFAULT_GENRE_TAXONOMY,
    GenreSemanticCategory,
)


def test_taxonomy_recognizes_representative_specific_genres() -> None:
    expected = {
        "K-pop": "K-pop",
        "technical death metal": "Technical Death Metal",
        "progressive metal": "Progressive Metal",
        "melodic death metal": "Melodic Death Metal",
        "drum and bass": "Drum and Bass",
    }
    for value, canonical_name in expected.items():
        result = DEFAULT_GENRE_TAXONOMY.classify(value)
        assert result.category is GenreSemanticCategory.GENRE
        assert result.canonical_name == canonical_name


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
    assert DEFAULT_GENRE_TAXONOMY.snapshot_id == DEFAULT_GENRE_TAXONOMY.snapshot_id
