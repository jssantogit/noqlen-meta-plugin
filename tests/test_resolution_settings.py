from dataclasses import replace

import pytest

from beetsplug.noqlenmeta.domain import MetadataCandidate
from beetsplug.noqlenmeta.integration import (
    ResolutionSettingsError,
    resolution_policy_from_settings,
)
from beetsplug.noqlenmeta.resolver import (
    ResolutionAction,
    default_resolution_policy,
    resolve_metadata,
)


def candidate(provider: str, confidence: float, value: int = 2005) -> MetadataCandidate:
    return MetadataCandidate(
        field="year",
        value=value,
        provider=provider,
        confidence=confidence,
        source_id=f"{provider}-release",
    )


def test_no_advanced_settings_preserve_the_pre_block_policy_exactly() -> None:
    field_settings = {"genres": False, "moods": True}
    provider_settings = {"discogs": True, "musicbrainz": True}
    baseline = default_resolution_policy()
    expected_rules = {
        field: replace(rule, enabled=field_settings.get(field, rule.enabled))
        for field, rule in baseline.field_rules.items()
    }
    expected_providers = {
        provider: provider_settings.get(provider, enabled)
        for provider, enabled in baseline.providers.items()
    }

    policy = resolution_policy_from_settings(field_settings, provider_settings)
    empty_policy = resolution_policy_from_settings(
        field_settings,
        provider_settings,
        authority_settings={},
        min_confidence_settings={},
        preserve_existing_settings={},
    )

    assert dict(policy.field_rules) == expected_rules
    assert dict(policy.providers) == expected_providers
    assert empty_policy == policy
    for field, rule in policy.field_rules.items():
        assert rule.enabled is expected_rules[field].enabled
        assert rule.authority == expected_rules[field].authority
        assert rule.min_confidence == expected_rules[field].min_confidence
        assert rule.preserve_existing is expected_rules[field].preserve_existing


def test_authority_override_replaces_order_and_drives_the_real_resolver() -> None:
    policy = resolution_policy_from_settings(
        {"year": True},
        {"discogs": True, "musicbrainz": True, "itunes": True},
        authority_settings={"year": [" Discogs ", "MusicBrainz", "ITUNES"]},
    )

    assert default_resolution_policy().field_rules["year"].authority[:3] == (
        "musicbrainz",
        "discogs",
        "itunes",
    )
    assert policy.field_rules["year"].authority == ("discogs", "musicbrainz", "itunes")
    decision = resolve_metadata(
        {},
        [candidate("discogs", 0.81), candidate("musicbrainz", 0.99, 2006)],
        policy,
    )[0]
    assert decision.selected == candidate("discogs", 0.81)


def test_lastfm_is_valid_in_custom_genres_authority() -> None:
    policy = resolution_policy_from_settings(
        {"genres": True},
        {"discogs": True, "lastfm": True, "itunes": True},
        authority_settings={"genres": ["lastfm", "discogs", "itunes"]},
    )

    assert policy.field_rules["genres"].authority == ("lastfm", "discogs", "itunes")


@pytest.mark.parametrize("field", ["lyrics", "synced_lyrics"])
def test_lrclib_is_valid_in_custom_lyrics_authority(field: str) -> None:
    policy = resolution_policy_from_settings(
        {field: True},
        {"lrclib": True},
        authority_settings={field: ["lrclib"]},
    )

    assert policy.field_rules[field].authority == ("lrclib",)
    assert policy.is_provider_enabled("lrclib")


def test_authority_override_leaves_every_omitted_field_unchanged() -> None:
    baseline = default_resolution_policy()
    policy = resolution_policy_from_settings(
        {},
        {},
        authority_settings={"year": ["discogs"]},
    )

    for field, rule in policy.field_rules.items():
        if field != "year":
            assert rule.authority == baseline.field_rules[field].authority


def test_confidence_override_is_field_level_and_drives_fallback_selection() -> None:
    policy = resolution_policy_from_settings(
        {"year": True},
        {"discogs": True, "musicbrainz": True},
        min_confidence_settings={"year": 0.95},
    )

    decision = resolve_metadata(
        {},
        [candidate("musicbrainz", 0.94), candidate("discogs", 0.96)],
        policy,
    )[0]
    assert decision.selected == candidate("discogs", 0.96)


def test_preserve_existing_override_changes_review_to_propose() -> None:
    default_policy = resolution_policy_from_settings(
        {"year": True},
        {"musicbrainz": True},
    )
    configured_policy = resolution_policy_from_settings(
        {"year": True},
        {"musicbrainz": True},
        preserve_existing_settings={"year": False},
    )
    proposal = candidate("musicbrainz", 0.99)

    default_decision = resolve_metadata({"year": 2006}, [proposal], default_policy)[0]
    configured_decision = resolve_metadata({"year": 2006}, [proposal], configured_policy)[0]

    assert default_decision.action is ResolutionAction.REVIEW
    assert configured_decision.action is ResolutionAction.PROPOSE


def test_all_overrides_apply_independently_to_one_final_rule() -> None:
    policy = resolution_policy_from_settings(
        {"year": True},
        {"discogs": True, "musicbrainz": True},
        authority_settings={"year": ["discogs", "musicbrainz"]},
        min_confidence_settings={"year": 0.9},
        preserve_existing_settings={"year": False},
    )

    rule = policy.field_rules["year"]
    assert rule.authority == ("discogs", "musicbrainz")
    assert rule.min_confidence == 0.9
    assert rule.preserve_existing is False


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"authority_settings": {"yeer": ["musicbrainz"]}}, "unknown field 'yeer'"),
        (
            {"authority_settings": {"year": "musicbrainz"}},
            "must be a sequence of provider names",
        ),
        ({"authority_settings": {"year": []}}, "must not be empty"),
        (
            {"authority_settings": {"year": ["musicbrainz", "MusicBrainz"]}},
            "must be unique",
        ),
        (
            {"authority_settings": {"year": ["musicbraimz"]}},
            "unknown provider 'musicbraimz'",
        ),
        ({"min_confidence_settings": {"yeer": 0.9}}, "unknown field 'yeer'"),
        ({"min_confidence_settings": {"year": -0.1}}, "minimum confidence"),
        ({"min_confidence_settings": {"year": 1.1}}, "minimum confidence"),
        ({"min_confidence_settings": {"year": True}}, "minimum confidence"),
        ({"min_confidence_settings": {"year": "0.9"}}, "minimum confidence"),
        ({"min_confidence_settings": {"year": float("nan")}}, "minimum confidence"),
        ({"min_confidence_settings": {"year": float("inf")}}, "minimum confidence"),
        ({"preserve_existing_settings": {"year": 0}}, "preserve_existing"),
        ({"preserve_existing_settings": {"year": 1}}, "preserve_existing"),
        ({"preserve_existing_settings": {"year": "false"}}, "preserve_existing"),
        ({"preserve_existing_settings": {"year": None}}, "preserve_existing"),
    ],
)
def test_invalid_explicit_overrides_fail_clearly(
    settings: dict[str, object], message: str
) -> None:
    with pytest.raises(ResolutionSettingsError, match=message):
        resolution_policy_from_settings({}, {}, **settings)  # type: ignore[arg-type]


def test_authority_and_capability_are_structurally_independent() -> None:
    policy = resolution_policy_from_settings(
        {"styles": True},
        {"itunes": True},
        authority_settings={"styles": ["itunes"]},
    )

    assert policy.field_rules["styles"].authority == ("itunes",)
