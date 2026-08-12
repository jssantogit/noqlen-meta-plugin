from beetsplug.noqlenmeta.authority import AUTHORITY_MATRIX
from beetsplug.noqlenmeta.beets_mapping import BEETS_FIELD_TARGETS
from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.field_contracts import FIELD_CONTRACTS, TargetClass, field_contract
from beetsplug.noqlenmeta.field_types import ALBUM_FIELD_TYPES, ITEM_FIELD_TYPES
from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_PROVIDER_CAPABILITIES,
    BUILTIN_PROVIDER_CAPABILITY_REGISTRY,
)
from beetsplug.noqlenmeta.track_mapping import TRACK_FIELD_TARGETS


def test_provider_capabilities_reference_field_registry() -> None:
    for capability in BUILTIN_PROVIDER_CAPABILITIES:
        assert capability.field in FIELD_CONTRACTS
        assert capability.asserted_entity in FIELD_CONTRACTS[capability.field].allowed_entities


def test_authority_matrix_references_registered_capabilities() -> None:
    for authority in AUTHORITY_MATRIX.rules:
        assert authority.asserted_entity in FIELD_CONTRACTS[authority.field].allowed_entities
        assert (
            authority.provider,
            authority.field,
            authority.asserted_entity,
            authority.acquisition_scope,
        ) in BUILTIN_PROVIDER_CAPABILITY_REGISTRY


def test_current_target_mappings_reference_field_registry() -> None:
    assert set(BEETS_FIELD_TARGETS) <= FIELD_CONTRACTS.keys()
    assert set(TRACK_FIELD_TARGETS) <= FIELD_CONTRACTS.keys()


def test_current_flexible_fields_reference_typed_db_contracts() -> None:
    for field in ITEM_FIELD_TYPES.keys() | ALBUM_FIELD_TYPES.keys():
        assert TargetClass.TYPED_DB in FIELD_CONTRACTS[field].target_classes


def test_public_v2_fields_resolve_to_registered_concepts() -> None:
    for field in default_config()["fields"]:
        assert field_contract(field)
