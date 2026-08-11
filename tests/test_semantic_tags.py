import pytest

from beetsplug.noqlenmeta.domain import SemanticCategory
from beetsplug.noqlenmeta.providers.specs import ProviderScope
from beetsplug.noqlenmeta.semantic_tags import classify_semantic_tag

CASES = (
    ("melancholy", SemanticCategory.MOOD, "Melancholic"),
    ("melancholic", SemanticCategory.MOOD, "Melancholic"),
    ("dreamy", SemanticCategory.MOOD, "Dreamy"),
    ("atmospheric", SemanticCategory.MOOD, "Atmospheric"),
    ("progressive metal", SemanticCategory.GENRE, "Progressive Metal"),
    ("technical death metal", SemanticCategory.GENRE, "Technical Death Metal"),
    ("k-pop", SemanticCategory.GENRE, "K-pop"),
    ("korean", SemanticCategory.ORIGIN, "Korean"),
    ("seen live", SemanticCategory.NOISE, "Seen Live"),
)


def classify(raw_tag: str):
    return classify_semantic_tag(
        raw_tag,
        "musicbrainz",
        ProviderScope.TRACK,
        0.9,
        "recording-id",
        "https://example.test/recording-id",
        8,
    )


@pytest.mark.parametrize(("raw_tag", "category", "canonical"), CASES)
def test_classifier_routes_each_tag_to_one_canonical_category(
    raw_tag: str, category: SemanticCategory, canonical: str
) -> None:
    evidence = classify(raw_tag)
    assert evidence is not None
    assert evidence.category is category
    assert evidence.canonical_term == canonical
    assert evidence.raw_tag == raw_tag


@pytest.mark.parametrize("raw_tag", ["", "  ", "unreviewed synthetic tag"])
def test_classifier_rejects_blank_and_unknown_tags(raw_tag: str) -> None:
    assert classify(raw_tag) is None


def test_classifier_reuses_genre_foundation_aliases() -> None:
    evidence = classify("dnb")
    assert evidence is not None
    assert evidence.category is SemanticCategory.GENRE
    assert evidence.canonical_term == "Drum and Bass"
