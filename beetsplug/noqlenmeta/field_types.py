"""Typed flexible fields owned by Noqlen Meta."""

from types import MappingProxyType

from beets.dbcore import types

from beetsplug.noqlenmeta.field_contracts import (
    V2_ALBUM_FLEXIBLE_FIELDS,
    V2_ITEM_FLEXIBLE_FIELDS,
)

ITEM_FIELD_TYPES = MappingProxyType(
    {
        **{field: types.MULTI_VALUE_DSV for field in V2_ITEM_FLEXIBLE_FIELDS},
        "isrcs": types.MULTI_VALUE_DSV,
        "iswcs": types.MULTI_VALUE_DSV,
        "mb_workids": types.MULTI_VALUE_DSV,
        "recording_date": types.STRING,
        "producers": types.MULTI_VALUE_DSV,
        "conductors": types.MULTI_VALUE_DSV,
        "performers": types.MULTI_VALUE_DSV,
        "featured_artists": types.MULTI_VALUE_DSV,
    }
)

ALBUM_FIELD_TYPES = MappingProxyType(
    {
        **{field: types.MULTI_VALUE_DSV for field in V2_ALBUM_FLEXIBLE_FIELDS},
        "edition": types.STRING,
        "release_secondary_types": types.MULTI_VALUE_DSV,
        "producers": types.MULTI_VALUE_DSV,
        "conductors": types.MULTI_VALUE_DSV,
        "performers": types.MULTI_VALUE_DSV,
        "featured_artists": types.MULTI_VALUE_DSV,
    }
)
