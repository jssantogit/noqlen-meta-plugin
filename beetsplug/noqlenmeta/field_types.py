"""Typed flexible fields owned by Noqlen Meta."""

from types import MappingProxyType

from beets.dbcore import types

from beetsplug.noqlenmeta.field_contracts import (
    V2_ALBUM_FLEXIBLE_FIELDS,
    V2_ITEM_FLEXIBLE_FIELDS,
)

ITEM_FIELD_TYPES = MappingProxyType(
    {field: types.MULTI_VALUE_DSV for field in V2_ITEM_FLEXIBLE_FIELDS}
)

ALBUM_FIELD_TYPES = MappingProxyType(
    {field: types.MULTI_VALUE_DSV for field in V2_ALBUM_FLEXIBLE_FIELDS}
)
