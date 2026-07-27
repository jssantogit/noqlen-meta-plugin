import pytest
from beets.autotag.hooks import TrackInfo
from beets.library import Item

from beetsplug.noqlenmeta.domain import MetadataCandidate, TrackEnrichmentContext
from beetsplug.noqlenmeta.resolver import FieldRule, ResolutionPolicy
from beetsplug.noqlenmeta.track_integration import SelectedImportTrack
from beetsplug.noqlenmeta.track_planning import build_import_track_planning_result
from beetsplug.noqlenmeta.track_preview import render_import_track_plan

PRIVATE_LYRIC = "PRIVATE-SYNTHETIC-LYRIC-CONTENT-DO-NOT-DISPLAY"
PRIVATE_SYNCED_LYRIC = "[00:01.00] PRIVATE-SYNTHETIC-SYNCED-CONTENT"


def _policy(
    *fields: str, preserve_existing: bool = True
) -> ResolutionPolicy:
    fields = fields or ("lyrics",)
    return ResolutionPolicy(
        {
            field: FieldRule(True, ("lrclib",), 0.8, preserve_existing)
            for field in fields
        },
        {"lrclib": True},
    )


def _result(
    current: str | None,
    candidate_value: str = PRIVATE_LYRIC,
    *,
    field: str = "lyrics",
    preserve_existing: bool = True,
):
    item = Item(**{field: current}) if current is not None else Item()
    track = TrackInfo(
        artist="Synthetic\x1b Artist",
        title="Synthetic\nTrack",
        album="Synthetic Album",
        length=180.0,
        index=2,
        medium=1,
        medium_index=2,
    )
    selected = SelectedImportTrack(item, track, None)
    return build_import_track_planning_result(
        selected,
        TrackEnrichmentContext(
            "Synthetic\x1b Artist",
            "Synthetic\nTrack",
            album_title="Synthetic Album",
            duration=180.0,
            track_number=2,
            disc_number=1,
        ),
        from_scratch=False,
        candidates=(MetadataCandidate(field, candidate_value, "lrclib", 0.95, "42"),),
        policy=_policy(field, preserve_existing=preserve_existing),
    )


@pytest.mark.parametrize(
    ("current", "candidate_value", "preserve_existing", "action"),
    [
        (None, PRIVATE_LYRIC, True, "PROPOSE"),
        ("different synthetic text", PRIVATE_LYRIC, True, "REVIEW"),
        (PRIVATE_LYRIC, PRIVATE_LYRIC, True, "KEEP"),
        ("different synthetic text", PRIVATE_LYRIC, False, "PROPOSE"),
    ],
)
def test_track_preview_actions_use_safe_content_summaries(
    monkeypatch: pytest.MonkeyPatch,
    current: str | None,
    candidate_value: str,
    preserve_existing: bool,
    action: str,
) -> None:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)

    render_import_track_plan(
        _result(current, candidate_value, preserve_existing=preserve_existing)
    )

    rendered = "\n".join(output)
    assert action in rendered
    assert "lyrics" in rendered
    assert "present (" in rendered
    assert "source: LRCLIB" in rendered
    assert "confidence: 0.95" in rendered
    assert f"mapped changes: {1 if action == 'PROPOSE' else 0}" in rendered
    assert "mapping blockers: 0" in rendered
    assert PRIVATE_LYRIC not in rendered
    assert "\x1b" not in rendered


def test_mapped_plain_lyrics_target_is_displayed_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)

    render_import_track_plan(_result(None))

    rendered = output[0]
    assert "mapped changes: 1" in rendered
    assert "mapping blockers: 0" in rendered
    assert "target: TrackInfo.lyrics" in rendered
    assert "mapping: lossless" in rendered
    assert PRIVATE_LYRIC not in rendered


def test_synced_lyrics_mapping_blocker_is_displayed_without_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)

    render_import_track_plan(
        _result(None, PRIVATE_SYNCED_LYRIC, field="synced_lyrics")
    )

    rendered = output[0]
    assert "synced_lyrics" in rendered
    assert "mapped changes: 0" in rendered
    assert "mapping blockers: 1" in rendered
    assert "target: unavailable" in rendered
    assert (
        "mapping blocker: no lossless normal beets TrackInfo target preserves "
        "synchronized lyrics semantics"
    ) in rendered
    assert PRIVATE_SYNCED_LYRIC not in rendered
    assert "[00:01.00]" not in rendered


def test_resolution_review_remains_distinct_from_mapping_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)

    render_import_track_plan(_result("Different synthetic text"))

    rendered = output[0]
    assert "REVIEW" in rendered
    assert "resolution review: 1" in rendered
    assert "mapping blockers: 0" in rendered
    assert "mapping blocker:" not in rendered
    assert "target: unavailable" not in rendered


def test_track_preview_reports_empty_candidate_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    output: list[str] = []
    monkeypatch.setattr("beetsplug.noqlenmeta.track_preview.ui.print_", output.append)
    track = TrackInfo(artist="Artist", title="Title")
    selected = SelectedImportTrack(Item(), track, None)
    result = build_import_track_planning_result(
        selected,
        TrackEnrichmentContext("Artist", "Title"),
        from_scratch=True,
        candidates=(),
        policy=_policy(),
    )

    render_import_track_plan(result)

    rendered = output[0]
    assert "from_scratch: yes" in rendered
    assert "provider candidates: 0" in rendered
    assert "planned changes: 0" in rendered
    assert "mapped changes: 0" in rendered
    assert "mapping blockers: 0" in rendered
    assert "no eligible track metadata candidates returned" in rendered
