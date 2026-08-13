import pytest

from beetsplug.noqlenmeta.authority import (
    AUTHORITY_MATRIX,
    AuthorityMatrix,
    AuthorityRole,
    AuthorityRule,
    eligible_standalone,
    translate_v2_authority,
)
from beetsplug.noqlenmeta.field_contracts import EntityKind
from beetsplug.noqlenmeta.providers.specs import ProviderScope


def rule(provider: str, role: AuthorityRole) -> AuthorityRule:
    return AuthorityRule(
        field="year",
        asserted_entity=EntityKind.RELEASE,
        acquisition_scope=ProviderScope.RELEASE,
        provider=provider,
        role=role,
    )


def test_unlisted_authority_is_ineligible() -> None:
    assert (
        AUTHORITY_MATRIX.role_for(
            "year",
            EntityKind.RELEASE,
            ProviderScope.RELEASE,
            "lastfm",
        )
        is AuthorityRole.INELIGIBLE
    )


def test_corroboration_only_cannot_be_selected_alone() -> None:
    assert not eligible_standalone(AuthorityRole.CORROBORATION_ONLY)
    assert not eligible_standalone(AuthorityRole.INELIGIBLE)
    assert eligible_standalone(AuthorityRole.PRIMARY)
    assert eligible_standalone(AuthorityRole.SECONDARY)
    assert eligible_standalone(AuthorityRole.FALLBACK)


def test_fallback_remains_distinct_from_secondary() -> None:
    assert (
        AUTHORITY_MATRIX.role_for("year", EntityKind.RELEASE, ProviderScope.RELEASE, "discogs")
        is AuthorityRole.SECONDARY
    )
    assert (
        AUTHORITY_MATRIX.role_for("year", EntityKind.RELEASE, ProviderScope.RELEASE, "itunes")
        is AuthorityRole.FALLBACK
    )


def test_duplicate_authority_rule_is_rejected() -> None:
    authority = rule("catalog", AuthorityRole.PRIMARY)
    with pytest.raises(ValueError, match="duplicate authority"):
        AuthorityMatrix((authority, authority))


def test_ineligible_rules_are_implicit_not_stored() -> None:
    with pytest.raises(ValueError, match="must remain unlisted"):
        AuthorityMatrix((rule("catalog", AuthorityRole.INELIGIBLE),))


def test_authority_rejects_entity_outside_field_contract() -> None:
    with pytest.raises(ValueError, match="allowed entities"):
        AuthorityRule(
            field="isrcs",
            asserted_entity=EntityKind.RELEASE,
            acquisition_scope=ProviderScope.RELEASE,
            provider="catalog",
            role=AuthorityRole.PRIMARY,
        )


def test_v2_ordered_authority_translation_preserves_exact_rank() -> None:
    translated = translate_v2_authority("year", ("itunes", "musicbrainz", "discogs"))

    assert [(entry.provider, entry.rank) for entry in translated] == [
        ("itunes", 0),
        ("musicbrainz", 1),
        ("discogs", 2),
    ]
    assert all(entry.field == "year" for entry in translated)


def test_v2_translation_does_not_guess_new_authority_roles() -> None:
    translated = translate_v2_authority("genres", ("lastfm", "discogs"))

    assert all(not hasattr(entry, "role") for entry in translated)


@pytest.mark.parametrize(
    ("field", "entity", "provider", "role"),
    [
        ("date", EntityKind.RELEASE, "musicbrainz", AuthorityRole.PRIMARY),
        ("date", EntityKind.RELEASE, "discogs", AuthorityRole.SECONDARY),
        ("date", EntityKind.RELEASE, "itunes", AuthorityRole.FALLBACK),
        (
            "original_date",
            EntityKind.RELEASE_GROUP,
            "musicbrainz",
            AuthorityRole.PRIMARY,
        ),
        (
            "release_type",
            EntityKind.RELEASE_GROUP,
            "musicbrainz",
            AuthorityRole.PRIMARY,
        ),
        (
            "release_secondary_types",
            EntityKind.RELEASE_GROUP,
            "musicbrainz",
            AuthorityRole.PRIMARY,
        ),
        (
            "release_status",
            EntityKind.RELEASE,
            "musicbrainz",
            AuthorityRole.PRIMARY,
        ),
        ("edition", EntityKind.RELEASE, "discogs", AuthorityRole.PRIMARY),
    ],
)
def test_release_catalog_authority_matches_implemented_capabilities(
    field: str,
    entity: EntityKind,
    provider: str,
    role: AuthorityRole,
) -> None:
    assert AUTHORITY_MATRIX.role_for(field, entity, ProviderScope.RELEASE, provider) is role


def test_original_year_has_no_independent_provider_authority() -> None:
    assert (
        AUTHORITY_MATRIX.role_for(
            "original_year",
            EntityKind.RELEASE_GROUP,
            ProviderScope.RELEASE,
            "musicbrainz",
        )
        is AuthorityRole.INELIGIBLE
    )
