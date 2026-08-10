"""Typed flexible fields owned by Noqlen Meta."""

from types import MappingProxyType

from beets.dbcore import types

ITEM_FIELD_TYPES = MappingProxyType(
    {
        "moods": types.MULTI_VALUE_DSV,
        "lyrics_languages": types.MULTI_VALUE_DSV,
        "artist_countries": types.MULTI_VALUE_DSV,
        "artist_areas": types.MULTI_VALUE_DSV,
        "artist_languages": types.MULTI_VALUE_DSV,
    }
)

ALBUM_FIELD_TYPES = MappingProxyType(
    {
        "styles": types.MULTI_VALUE_DSV,
        "artist_countries": types.MULTI_VALUE_DSV,
        "artist_areas": types.MULTI_VALUE_DSV,
        "artist_languages": types.MULTI_VALUE_DSV,
    }
)
