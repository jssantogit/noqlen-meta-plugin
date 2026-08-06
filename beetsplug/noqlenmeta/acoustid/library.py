from __future__ import annotations

from beets.library import Library

from beetsplug.noqlenmeta.identity.library import (
    LibraryIdentityTargetKind,
    SelectedLibraryIdentityTarget,
    refresh_library_identity_target,
    select_library_identity_targets,
)

from .domain import (
    AcoustIDExistingValues,
    AcoustIDLibraryTargetKind,
    SelectedAcoustIDItem,
    SelectedAcoustIDTarget,
)


def select_acoustid_targets(
    library: Library, query: object = None
) -> tuple[SelectedAcoustIDTarget, ...]:
    if type(library) is not Library:
        raise TypeError("AcoustID selection requires a supported Library")
    return tuple(
        _convert_target(target) for target in select_library_identity_targets(library, query)
    )


def refresh_acoustid_target(
    library: Library, selected: SelectedAcoustIDTarget
) -> SelectedAcoustIDTarget:
    if type(library) is not Library:
        raise TypeError("AcoustID refresh requires a supported Library")
    if type(selected) is not SelectedAcoustIDTarget:
        raise TypeError("AcoustID refresh requires a selected target")
    if type(selected._refresh_source) is not SelectedLibraryIdentityTarget:
        raise ValueError("AcoustID target cannot be refreshed")
    source = selected._refresh_source
    if (
        source.kind.value != selected.kind.value
        or source.album_id != selected.album_id
        or tuple(item.item_id for item in source.items)
        != tuple(item.item_id for item in selected.items)
        or tuple(item.local_key for item in source.items)
        != tuple(item.local_key for item in selected.items)
    ):
        raise ValueError("AcoustID refresh source is inconsistent")
    fresh = refresh_library_identity_target(library, source)
    return _convert_target(fresh)


def _convert_target(selected: SelectedLibraryIdentityTarget) -> SelectedAcoustIDTarget:
    kind = (
        AcoustIDLibraryTargetKind.ALBUM
        if selected.kind is LibraryIdentityTargetKind.ALBUM
        else AcoustIDLibraryTargetKind.SINGLETON
    )
    return SelectedAcoustIDTarget(
        kind,
        selected.album_id,
        tuple(
            SelectedAcoustIDItem(
                selected_item.local_key,
                selected_item.item_id,
                selected.album_id,
                selected_item.item,
                selected_item.item.path,
                AcoustIDExistingValues.from_stored(
                    selected_item.item.acoustid_id,
                    selected_item.item.acoustid_fingerprint,
                    selected_item.item.length,
                ),
            )
            for selected_item in selected.items
        ),
        selected,
    )
