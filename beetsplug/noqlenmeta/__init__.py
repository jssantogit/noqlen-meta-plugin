"""Noqlen Meta beets plugin."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

import confuse
from beets import ui
from beets.autotag import AlbumMatch, TrackMatch
from beets.library import Album, Library
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDLookupService,
    AcoustIDSettings,
    FingerprintBackend,
    FpcalcFingerprintBackend,
    acoustid_target_from_library_identity,
    apply_acoustid_results,
    plan_acoustid_target,
    prepare_fingerprint,
    render_acoustid_preview,
    select_acoustid_targets,
)
from beetsplug.noqlenmeta.beets_application import (
    BeetsApplicationMode,
    apply_beets_target_plan,
    parse_application_mode,
)
from beetsplug.noqlenmeta.beets_mapping import map_change_plan_to_beets
from beetsplug.noqlenmeta.changeplan import ChangePlan, build_change_plan
from beetsplug.noqlenmeta.configuration import default_config
from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    MetadataValue,
    ReleaseEnrichmentContext,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.field_types import ALBUM_FIELD_TYPES, ITEM_FIELD_TYPES
from beetsplug.noqlenmeta.file_sync import (
    FileSyncPlan,
    apply_file_sync_plan,
    plan_file_sync,
    verify_file_sync_plan,
)
from beetsplug.noqlenmeta.identity import (
    AcoustIDRecordingExpectations,
    BeetsMusicBrainzIdentitySource,
    IdentityImportApplicationResult,
    IdentitySourceError,
    ImportIdentityAuditResult,
    MusicBrainzIdentitySource,
    apply_import_identity_plan,
    audit_identity_candidate_evaluations,
    audit_with_musicbrainz_source,
    identity_context_from_selected_import,
    map_identity_audit_to_import_targets,
    rank_identity_candidates,
    selected_import_identity,
)
from beetsplug.noqlenmeta.identity.importer_preview import (
    render_import_identity_audit,
    render_incomplete_import_identity_note,
)
from beetsplug.noqlenmeta.identity.library import (
    LibraryIdentityAuditResult,
    LibraryIdentityContextResult,
    SelectedLibraryIdentityTarget,
    exact_snapshot_from_library_target,
    identity_context_from_library_target,
    refresh_library_identity_target,
    select_library_identity_targets,
)
from beetsplug.noqlenmeta.identity.library_application import (
    LibraryIdentityApplicationError,
    apply_library_identity_plan,
    verify_library_identity_plan_snapshot,
)
from beetsplug.noqlenmeta.identity.library_mapping import (
    LibraryIdentityTargetPlan,
    map_library_identity_targets,
)
from beetsplug.noqlenmeta.identity.library_preview import (
    render_library_identity_audit,
    render_unavailable_library_identity_target,
)
from beetsplug.noqlenmeta.identity.tag_application import (
    IdentityTagApplicationError,
    apply_identity_tag_file_plan,
    verify_identity_tag_file_plan,
)
from beetsplug.noqlenmeta.identity.tag_mapping import plan_identity_tag_targets
from beetsplug.noqlenmeta.identity.tag_preview import render_identity_tag_plan
from beetsplug.noqlenmeta.identity.tag_sync import prepare_identity_tag_database_target
from beetsplug.noqlenmeta.integration import (
    ResolutionSettingsError,
    context_from_album_info,
    current_values_from_album_info,
    eligible_album_info,
    render_beets_target_plan,
    resolution_policy_from_settings,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.library_application import (
    LibraryApplicationMode,
    LibraryApplicationResult,
    apply_library_target_plan,
)
from beetsplug.noqlenmeta.library_integration import (
    context_from_library_album,
    current_values_from_library_album,
    render_library_target_plan,
)
from beetsplug.noqlenmeta.library_mapping import (
    LibraryTargetPlan,
    map_change_plan_to_library_album,
)
from beetsplug.noqlenmeta.orchestration import (
    provider_can_contribute,
    validate_provider_candidates,
)
from beetsplug.noqlenmeta.providers import ProviderError
from beetsplug.noqlenmeta.providers.specs import (
    BUILTIN_PROVIDER_NAMES,
    BUILTIN_RELEASE_PROVIDER_SPECS,
    BUILTIN_TRACK_PROVIDER_SPECS,
    DISCOGS_SPEC,
    ITUNES_SPEC,
    LASTFM_SPEC,
    LRCLIB_SPEC,
    MUSICBRAINZ_SPEC,
    ProviderSpec,
)
from beetsplug.noqlenmeta.resolver import ResolutionPolicy, resolve_metadata
from beetsplug.noqlenmeta.track_application import (
    TrackApplicationMode,
    TrackApplicationResult,
    apply_track_target_plan,
    parse_track_application_mode,
)
from beetsplug.noqlenmeta.track_integration import (
    SelectedImportTrack,
    context_from_selected_import_track,
    selected_import_tracks,
)
from beetsplug.noqlenmeta.track_planning import (
    ImportTrackPlanningResult,
    build_import_track_planning_result,
)
from beetsplug.noqlenmeta.track_preview import (
    render_import_track_plan,
    render_incomplete_track_note,
)

_FIELD_DEFAULTS = default_config()["fields"]
_RESOLUTION_SECTIONS = frozenset({"authority", "min_confidence", "preserve_existing"})


def _identity_backend_forbidden() -> FingerprintBackend:
    raise RuntimeError("fingerprint generation is forbidden during identity audit")


class IdentityImporterSettingsError(RuntimeError):
    """Raised before provider work when importer identity settings are unsafe."""


@dataclass(frozen=True, slots=True)
class LibraryAlbumPlan:
    """One prepared command plan retained until every Album is planned."""

    album: Album
    target_plan: LibraryTargetPlan
    position: int
    total: int


@dataclass(frozen=True, slots=True)
class PreparedLibraryIdentityPlan:
    selected: SelectedLibraryIdentityTarget
    context_result: LibraryIdentityContextResult | None
    result: LibraryIdentityAuditResult | None
    target_plan: LibraryIdentityTargetPlan | None
    unavailable_reason: str | None
    position: int
    total: int


class NoqlenMetaPlugin(BeetsPlugin):
    """Entry point loaded by beets as the ``noqlenmeta`` plugin."""

    item_types = dict(ITEM_FIELD_TYPES)

    @property
    def album_types(self) -> dict[str, object]:
        return dict(ALBUM_FIELD_TYPES)

    def __init__(self) -> None:
        super().__init__()
        self.config.add(default_config())
        self.config["providers"]["discogs"]["user_token"].redact = True
        self._lastfm_provider = None
        self._lrclib_provider = None
        self._musicbrainz_identity_source: MusicBrainzIdentitySource | None = None
        self.register_listener("import_task_choice", self._import_task_choice)
        self._command = Subcommand(
            "noqlenmeta",
            help="preview or apply metadata and MusicBrainz identity workflows",
            aliases=["nm"],
        )
        self._command.parser.add_option(
            "--identity",
            dest="identity",
            action="store_true",
            default=False,
            help="audit MusicBrainz identity; --apply repairs database fields only",
        )
        self._command.parser.add_option(
            "--identity-tags",
            dest="identity_tags",
            action="store_true",
            default=False,
            help=(
                "preview synchronization of MusicBrainz identity from the database "
                "to media-file tags"
            ),
        )
        self._command.parser.add_option(
            "--acoustid",
            dest="acoustid",
            action="store_true",
            default=False,
            help="preview or apply existing-library AcoustID database evidence",
        )
        self._command.parser.add_option(
            "--fingerprint-missing",
            dest="fingerprint_missing",
            action="store_true",
            default=False,
            help="with --acoustid, permit calculation of missing fingerprints",
        )
        self._command.parser.add_option(
            "--all",
            dest="all",
            action="store_true",
            default=False,
            help="process all targets in the selected mode instead of using a query",
        )
        self._command.parser.add_option(
            "--apply",
            dest="apply",
            action="store_true",
            default=False,
            help="apply ordinary metadata or identity repair to the database; never writes files",
        )
        self._command.parser.add_option(
            "--partial",
            dest="partial",
            action="store_true",
            default=False,
            help="ordinary metadata only: with --apply, store safe fields and withhold blockers",
        )
        self._command.parser.add_option(
            "--write",
            dest="write",
            action="store_true",
            default=False,
            help="with --identity-tags, replace eligible files after verified tag synchronization",
        )
        self._command.func = self._command_noqlenmeta

    def commands(self) -> list[Subcommand]:
        return [self._command]

    def _import_task_choice(self, session: object, task: object) -> None:
        identity_enabled, identity_preview, identity_apply = self._identity_settings()
        album_info = eligible_album_info(task)
        selected_tracks = selected_import_tracks(task)
        selected_identity = selected_import_identity(task)
        if album_info is None and not selected_tracks and selected_identity is None:
            return

        apply_enabled = self.config["apply"].get(bool)
        application_mode = BeetsApplicationMode.STRICT
        track_application_mode = TrackApplicationMode.STRICT
        if apply_enabled:
            raw_mode = self.config["apply_mode"].as_str()
            application_mode = parse_application_mode(raw_mode)
            track_application_mode = parse_track_application_mode(raw_mode)

        policy = self._resolution_policy()
        release_can_contribute = (
            album_info is not None and self._has_contributing_release_provider(policy)
        )
        preview_enabled = self.config["preview"].get(bool)
        track_can_contribute = (
            bool(selected_tracks)
            and self._has_contributing_track_provider(policy)
            and (preview_enabled or apply_enabled)
        )
        identity_can_execute = (
            identity_enabled
            and (identity_preview or identity_apply)
            and selected_identity is not None
        )
        if not release_can_contribute and not track_can_contribute and not identity_can_execute:
            return

        match = getattr(task, "match", None)
        from_scratch = None
        if track_can_contribute or identity_can_execute:
            if not isinstance(match, (AlbumMatch, TrackMatch)):
                raise TypeError("selected importer metadata requires a beets match")
            from_scratch = match.from_scratch(None)

        if release_can_contribute and album_info is not None:
            context = context_from_album_info(album_info)
            if context is None:
                self._log.debug(
                    "Noqlen Meta preview skipped: selected release has no album identity"
                )
            else:
                change_plan = self._build_change_plan_for_release(
                    context,
                    current_values_from_album_info(album_info),
                    policy,
                )
                target_plan = map_change_plan_to_beets(change_plan)
                application_result = None
                if apply_enabled:
                    application_result = apply_beets_target_plan(
                        album_info,
                        target_plan,
                        mode=application_mode,
                    )
                if preview_enabled:
                    render_beets_target_plan(target_plan, application_result)
                elif apply_enabled and application_result is not None:
                    if application_result.is_blocked:
                        self._log.warning(
                            "Noqlen Meta: application blocked by unresolved review or "
                            "target mapping"
                        )
                    elif application_result.has_applied_changes:
                        if application_result.has_withheld_fields:
                            self._log.info(
                                "Noqlen Meta: prepared {} selected-release metadata "
                                "field(s) for beets application; {} review and {} mapping "
                                "blocker withheld",
                                len(application_result.applied_changes),
                                application_result.resolution_review_count,
                                application_result.mapping_blocker_count,
                            )
                        else:
                            self._log.info(
                                "Noqlen Meta: prepared {} selected-release metadata "
                                "field(s) for beets application",
                                len(application_result.applied_changes),
                            )
                    elif (
                        application_result.mode is BeetsApplicationMode.PARTIAL
                        and application_result.has_withheld_fields
                    ):
                        withheld_count = (
                            application_result.resolution_review_count
                            + application_result.mapping_blocker_count
                        )
                        self._log.warning(
                            "Noqlen Meta: no eligible selected-release metadata changes; "
                            "{} unresolved field(s) withheld",
                            withheld_count,
                        )
                    else:
                        self._log.info(
                            "Noqlen Meta: no selected-release metadata changes prepared "
                            "for beets application"
                        )

        if track_can_contribute:
            assert from_scratch is not None
            for selected in selected_tracks:
                context = context_from_selected_import_track(selected)
                if context is None:
                    if preview_enabled:
                        render_incomplete_track_note()
                    continue
                planning_result = self._build_import_track_plan(
                    selected,
                    context,
                    from_scratch=from_scratch,
                    policy=policy,
                )
                track_application_result = None
                if apply_enabled:
                    track_application_result = apply_track_target_plan(
                        selected,
                        planning_result.target_plan,
                        from_scratch=from_scratch,
                        mode=track_application_mode,
                    )
                if preview_enabled:
                    render_import_track_plan(planning_result, track_application_result)
                elif track_application_result is not None:
                    self._log_track_application_result(track_application_result)

        if identity_can_execute:
            assert selected_identity is not None
            assert from_scratch is not None
            identity_context = identity_context_from_selected_import(
                selected_identity,
                from_scratch=from_scratch,
            )
            if identity_context is None:
                if identity_preview:
                    render_incomplete_import_identity_note()
                else:
                    self._log.warning(
                        "Noqlen Meta: selected import has insufficient identity structure "
                        "for MusicBrainz audit"
                    )
                return
            try:
                identity_audit = audit_with_musicbrainz_source(
                    identity_context,
                    self._identity_source(),
                )
            except IdentitySourceError:
                self._log.warning("Noqlen Meta: MusicBrainz identity audit unavailable")
                return
            identity_result = ImportIdentityAuditResult(
                selected_identity,
                identity_context,
                identity_audit,
            )
            identity_target_plan = map_identity_audit_to_import_targets(
                identity_result.audit,
                match_kind=selected_identity.kind,
            )
            identity_application_result = None
            if identity_apply:
                identity_application_result = apply_import_identity_plan(
                    selected_identity,
                    identity_target_plan,
                    from_scratch=from_scratch,
                )
            if identity_preview:
                render_import_identity_audit(
                    identity_result,
                    identity_target_plan,
                    identity_application_result,
                )
            elif identity_application_result is not None:
                self._log_identity_application_result(identity_application_result)

    def _identity_settings(self) -> tuple[bool, bool, bool]:
        try:
            enabled = self.config["identity"]["enabled"].get(bool)
            preview = self.config["identity"]["preview"].get(bool)
            apply = self.config["identity"]["apply"].get(bool)
        except confuse.ConfigError as error:
            raise IdentityImporterSettingsError("identity settings must be booleans") from error
        if not enabled and apply:
            raise IdentityImporterSettingsError(
                "identity application requires identity to be enabled"
            )
        return enabled, preview, apply

    def _identity_source(self) -> MusicBrainzIdentitySource:
        if self._musicbrainz_identity_source is None:
            self._musicbrainz_identity_source = BeetsMusicBrainzIdentitySource()
        return self._musicbrainz_identity_source

    def _acoustid_settings(self) -> AcoustIDSettings:
        try:
            values = self.config["acoustid"].get(dict)
            return AcoustIDSettings.from_mapping(values)
        except (confuse.ConfigError, ValueError) as error:
            raise ui.UserError("noqlenmeta: invalid AcoustID configuration") from error

    def _log_identity_application_result(
        self, result: IdentityImportApplicationResult
    ) -> None:
        if result.is_blocked:
            self._log.warning(
                "Noqlen Meta: MusicBrainz identity repair blocked by ambiguous evidence"
            )
        elif result.is_confirmed_noop:
            self._log.info("Noqlen Meta: selected MusicBrainz identity already confirmed")
        elif result.has_applied_changes:
            self._log.info(
                "Noqlen Meta: prepared {} MusicBrainz identity field(s) for beets application",
                len(result.applied_changes),
            )

    def _log_track_application_result(self, result: TrackApplicationResult) -> None:
        """Log one application outcome without selected identity or metadata values."""
        if result.is_blocked:
            self._log.warning(
                "Noqlen Meta: selected-track application blocked by unresolved review or "
                "target mapping"
            )
        elif result.has_applied_changes:
            if result.has_withheld_fields:
                self._log.info(
                    "Noqlen Meta: prepared {} selected-track metadata field(s) for beets "
                    "application; {} review and {} mapping blocker withheld",
                    len(result.applied_changes),
                    result.resolution_review_count,
                    result.mapping_blocker_count,
                )
            else:
                self._log.info(
                    "Noqlen Meta: prepared {} selected-track metadata field(s) for beets "
                    "application",
                    len(result.applied_changes),
                )
        elif result.mode is TrackApplicationMode.PARTIAL and result.has_withheld_fields:
            withheld_count = result.resolution_review_count + result.mapping_blocker_count
            self._log.warning(
                "Noqlen Meta: no eligible selected-track metadata changes; {} unresolved "
                "field(s) withheld",
                withheld_count,
            )
        else:
            self._log.info(
                "Noqlen Meta: no selected-track metadata changes prepared for beets application"
            )

    def _command_noqlenmeta(self, lib: Library, opts: object, args: list[str]) -> None:
        identity_enabled = bool(getattr(opts, "identity", False))
        identity_tags_enabled = bool(getattr(opts, "identity_tags", False))
        acoustid_enabled = bool(getattr(opts, "acoustid", False))
        fingerprint_missing = bool(getattr(opts, "fingerprint_missing", False))
        write_enabled = bool(getattr(opts, "write", False))
        apply_enabled = bool(getattr(opts, "apply", False))
        partial_enabled = bool(getattr(opts, "partial", False))
        if acoustid_enabled and identity_enabled:
            raise ui.UserError("noqlenmeta: --acoustid cannot be used with --identity")
        if acoustid_enabled and identity_tags_enabled:
            raise ui.UserError("noqlenmeta: --acoustid cannot be used with --identity-tags")
        if acoustid_enabled and write_enabled:
            raise ui.UserError("noqlenmeta: --acoustid cannot be used with --write")
        if acoustid_enabled and partial_enabled:
            raise ui.UserError("noqlenmeta: --acoustid cannot be used with --partial")
        if fingerprint_missing and not acoustid_enabled:
            raise ui.UserError("noqlenmeta: --fingerprint-missing requires --acoustid")
        if identity_enabled and identity_tags_enabled:
            raise ui.UserError("noqlenmeta: --identity and --identity-tags are mutually exclusive")
        if write_enabled and not identity_tags_enabled and not apply_enabled:
            raise ui.UserError("noqlenmeta: --write requires --apply for ordinary metadata")
        if identity_tags_enabled and apply_enabled:
            raise ui.UserError("noqlenmeta: --identity-tags cannot be used with --apply")
        if identity_tags_enabled and partial_enabled:
            raise ui.UserError("noqlenmeta: --identity-tags cannot be used with --partial")
        if identity_enabled:
            self._command_library_identity(lib, opts, args)
            return
        if identity_tags_enabled:
            self._command_identity_tags(lib, opts, args)
            return
        if acoustid_enabled:
            self._command_acoustid(lib, opts, args)
            return
        all_albums = bool(getattr(opts, "all", False))
        if partial_enabled and not apply_enabled:
            raise ui.UserError("noqlenmeta: --partial requires --apply")
        application_mode = (
            LibraryApplicationMode.PARTIAL
            if partial_enabled
            else LibraryApplicationMode.STRICT
        )
        has_query = any(isinstance(argument, str) and argument.strip() for argument in args)
        if not has_query and not all_albums:
            raise ui.UserError("noqlenmeta: provide an album query or use --all")
        if args and all_albums:
            raise ui.UserError("noqlenmeta: use an album query or --all, not both")

        policy = self._resolution_policy()
        if not self._has_contributing_release_provider(policy):
            ui.print_("Noqlen Meta: no enabled provider can contribute to the configured fields")
            return

        albums = tuple(lib.albums(args if args else None))
        if not albums:
            ui.print_("Noqlen Meta: no albums matched")
            return

        prepared: list[LibraryAlbumPlan] = []
        total = len(albums)
        for position, album in enumerate(albums, 1):
            context = context_from_library_album(album)
            if context is None:
                ui.print_(
                    f"Noqlen Meta: [{position}/{total}] album has no usable "
                    "artist/title identity; skipped"
                )
                continue
            change_plan = self._build_change_plan_for_release(
                context,
                current_values_from_library_album(album),
                policy,
            )
            prepared.append(
                LibraryAlbumPlan(
                    album,
                    map_change_plan_to_library_album(change_plan),
                    position,
                    total,
                )
            )

        file_plans: list[FileSyncPlan] = []
        if write_enabled:
            for album_plan in prepared:
                target_plan = album_plan.target_plan
                changes = (
                    tuple(change.source for change in target_plan.mapped_changes)
                    if application_mode is LibraryApplicationMode.PARTIAL
                    or not target_plan.requires_review
                    else ()
                )
                for item in album_plan.album.items():
                    file_plans.append(plan_file_sync(item, changes))
            for album_plan in prepared:
                render_library_target_plan(
                    album_plan.album,
                    album_plan.target_plan,
                    None,
                    position=album_plan.position,
                    total=album_plan.total,
                )
            for file_plan in file_plans:
                ui.print_(
                    "Noqlen Meta / file plan: "
                    f"Item {file_plan.item_id}; changes={len(file_plan.changes)}; "
                    f"blockers={len(file_plan.blockers)}"
                )
            for file_plan in file_plans:
                verify_file_sync_plan(lib, file_plan)

        application_results: list[LibraryApplicationResult | None] = []
        for album_plan in prepared:
            application_results.append(
                apply_library_target_plan(
                    album_plan.album,
                    album_plan.target_plan,
                    mode=application_mode,
                )
                if apply_enabled
                else None
            )

        file_results = (
            tuple(apply_file_sync_plan(lib, file_plan) for file_plan in file_plans)
            if write_enabled
            else ()
        )

        for album_plan, application_result in zip(
            prepared, application_results, strict=True
        ):
            if write_enabled:
                continue
            render_library_target_plan(
                album_plan.album,
                album_plan.target_plan,
                application_result,
                position=album_plan.position,
                total=album_plan.total,
            )
        for result in file_results:
            status = "committed" if result.committed else "blocked"
            ui.print_(
                "Noqlen Meta / file application: "
                f"Item {result.item_id}; status={status}; "
                f"fields={len(result.applied_fields)}"
            )

    def _command_identity_tags(
        self, lib: Library, opts: object, args: list[str]
    ) -> None:
        all_items = bool(getattr(opts, "all", False))
        write_enabled = bool(getattr(opts, "write", False))
        has_query = any(isinstance(argument, str) and argument.strip() for argument in args)
        if not has_query and not all_items:
            raise ui.UserError("noqlenmeta: --identity-tags requires an Item query or --all")
        if args and all_items:
            raise ui.UserError(
                "noqlenmeta: use an Item query or --all with --identity-tags, not both"
            )

        selected = select_library_identity_targets(lib, args if args else None)
        if not selected:
            ui.print_("Noqlen MusicBrainz identity tags: no Items matched")
            return
        database_targets = tuple(
            prepare_identity_tag_database_target(lib, target) for target in selected
        )
        target_plans = plan_identity_tag_targets(database_targets)
        total = sum(len(target.files) for target in target_plans)

        if write_enabled:
            for target_plan in target_plans:
                for plan in target_plan.files:
                    if plan.blocked_reason is None:
                        verify_identity_tag_file_plan(lib, target_plan.database, plan)

        position = 0
        earlier_changes_committed = False
        for target_plan in target_plans:
            for plan in target_plan.files:
                position += 1
                result = None
                if write_enabled:
                    try:
                        result = apply_identity_tag_file_plan(lib, target_plan.database, plan)
                    except IdentityTagApplicationError as error:
                        if earlier_changes_committed and not error.committed:
                            raise IdentityTagApplicationError(
                                "identity tag command stopped after earlier file changes "
                                "were committed",
                                integrity_critical=error.integrity_critical,
                                committed=True,
                            ) from error
                        raise
                render_identity_tag_plan(
                    plan,
                    result,
                    write_requested=write_enabled,
                    position=position,
                    total=total,
                )
                if result is not None:
                    earlier_changes_committed = (
                        earlier_changes_committed or result.has_applied_changes
                    )

    def _command_library_identity(
        self, lib: Library, opts: object, args: list[str]
    ) -> None:
        all_items = bool(getattr(opts, "all", False))
        apply_enabled = bool(getattr(opts, "apply", False))
        partial_enabled = bool(getattr(opts, "partial", False))
        has_query = any(isinstance(argument, str) and argument.strip() for argument in args)
        if partial_enabled:
            raise ui.UserError("noqlenmeta: --identity cannot be used with --partial")
        if not has_query and not all_items:
            raise ui.UserError("noqlenmeta: --identity requires an Item query or --all")
        if args and all_items:
            raise ui.UserError("noqlenmeta: use an Item query or --all with --identity, not both")

        acoustid_settings = self._acoustid_settings()
        targets = select_library_identity_targets(lib, args if args else None)
        if not targets:
            ui.print_("Noqlen MusicBrainz identity: no Items matched")
            return

        context_results = tuple(identity_context_from_library_target(target) for target in targets)
        source = self._identity_source() if any(context_results) else None
        acoustid_lookup = (
            AcoustIDLookupService(acoustid_settings)
            if acoustid_settings.enabled and acoustid_settings.use_for_identity
            else None
        )
        prepared: list[PreparedLibraryIdentityPlan] = []
        total = len(targets)
        for position, (target, context_result) in enumerate(
            zip(targets, context_results, strict=True), start=1
        ):
            if context_result is None:
                prepared.append(
                    PreparedLibraryIdentityPlan(
                        target, None, None, None, "context", position, total
                    )
                )
                continue
            assert source is not None
            try:
                candidates = source.candidates_for(context_result.context)
                evaluations = rank_identity_candidates(context_result.context, candidates)
                expectations = (
                    self._identity_acoustid_expectations(
                        target, acoustid_settings, acoustid_lookup
                    )
                    if acoustid_lookup is not None and evaluations
                    else None
                )
                audit = audit_identity_candidate_evaluations(
                    context_result.context,
                    evaluations,
                    acoustid_expectations=expectations,
                )
                result = LibraryIdentityAuditResult(context_result, audit)
            except IdentitySourceError:
                prepared.append(
                    PreparedLibraryIdentityPlan(
                        target,
                        context_result,
                        None,
                        None,
                        "source",
                        position,
                        total,
                    )
                )
                continue
            if result is None:
                prepared.append(
                    PreparedLibraryIdentityPlan(
                        target, None, None, None, "context", position, total
                    )
                )
                continue
            prepared.append(
                PreparedLibraryIdentityPlan(
                    target,
                    result.context_result,
                    result,
                    None,
                    None,
                    position,
                    total,
                )
            )

        # Keep mapping as a distinct phase after every source call and audit has completed.
        prepared = [
            replace(record, target_plan=map_library_identity_targets(record.result))
            if record.result is not None
            else record
            for record in prepared
        ]

        if apply_enabled:
            # Every source call and mapping is complete before this command-wide stale preflight.
            for record in prepared:
                if record.target_plan is not None:
                    verify_library_identity_plan_snapshot(lib, record.target_plan)
                elif record.context_result is not None:
                    fresh = refresh_library_identity_target(lib, record.selected)
                    if exact_snapshot_from_library_target(
                        fresh
                    ) != record.context_result.exact_snapshot:
                        raise LibraryIdentityApplicationError(
                            "library identity unavailable target is stale"
                        )
            earlier_changes_committed = False
            for record in prepared:
                if record.result is None or record.target_plan is None:
                    render_unavailable_library_identity_target(
                        record.selected,
                        position=record.position,
                        total=record.total,
                        source_unavailable=record.unavailable_reason == "source",
                    )
                    continue
                try:
                    application_result = apply_library_identity_plan(lib, record.target_plan)
                except LibraryIdentityApplicationError as error:
                    if earlier_changes_committed:
                        raise LibraryIdentityApplicationError(
                            "library identity command stopped after earlier target changes "
                            "were committed",
                            integrity_critical=error.integrity_critical,
                            committed=True,
                        ) from error
                    raise
                render_library_identity_audit(
                    record.result,
                    record.target_plan,
                    application_result,
                    apply_requested=True,
                    position=record.position,
                    total=record.total,
                )
                earlier_changes_committed = (
                    earlier_changes_committed or application_result.has_applied_changes
                )
            return

        for record in prepared:
            if record.result is None or record.target_plan is None:
                render_unavailable_library_identity_target(
                    record.selected,
                    position=record.position,
                    total=record.total,
                    source_unavailable=record.unavailable_reason == "source",
                )
                continue
            render_library_identity_audit(
                record.result,
                record.target_plan,
                None,
                apply_requested=False,
                position=record.position,
                total=record.total,
            )

    def _identity_acoustid_expectations(
        self,
        selected: SelectedLibraryIdentityTarget,
        settings: AcoustIDSettings,
        lookup_service: AcoustIDLookupService,
    ) -> AcoustIDRecordingExpectations:
        target = acoustid_target_from_library_identity(selected)
        identity_settings = replace(settings, compute_missing=False)
        evidence = []
        for item in target.items:
            preparation = prepare_fingerprint(
                item,
                identity_settings,
                False,
                _identity_backend_forbidden,
            )
            if preparation.material is not None:
                evidence.append(lookup_service.lookup(preparation.material))
        return AcoustIDRecordingExpectations.from_evidence(tuple(evidence))

    def _command_acoustid(self, lib: Library, opts: object, args: list[str]) -> None:
        all_items = bool(getattr(opts, "all", False))
        apply_enabled = bool(getattr(opts, "apply", False))
        fingerprint_missing = bool(getattr(opts, "fingerprint_missing", False))
        has_query = any(isinstance(argument, str) and argument.strip() for argument in args)
        if not has_query and not all_items:
            raise ui.UserError("noqlenmeta: --acoustid requires an Item query or --all")
        if args and all_items:
            raise ui.UserError("noqlenmeta: use an Item query or --all with --acoustid, not both")

        settings = self._acoustid_settings()
        targets = select_acoustid_targets(lib, args if args else None)
        if not targets:
            ui.print_("Noqlen AcoustID: no Items matched")
            return
        lookup_service = AcoustIDLookupService(settings)
        backend: FingerprintBackend | None = None

        def backend_factory() -> FingerprintBackend:
            nonlocal backend
            if backend is None:
                backend = FpcalcFingerprintBackend.from_settings(settings)
            return backend

        results = tuple(
            plan_acoustid_target(
                target,
                settings,
                fingerprint_missing,
                backend_factory,
                lookup_service,
            )
            for target in targets
        )
        for result in results:
            ui.print_(render_acoustid_preview(result))
        application_result = apply_acoustid_results(lib, results) if apply_enabled else None
        if application_result is not None:
            ui.print_(
                "AcoustID application: "
                f"targets={application_result.target_count} "
                f"changed_targets={application_result.changed_target_count} "
                f"changed_items={application_result.changed_item_count} "
                f"fields={application_result.applied_field_count}"
            )

    def _resolution_policy(self) -> ResolutionPolicy:
        field_settings = {
            field: self.config["fields"][field].get(bool) for field in _FIELD_DEFAULTS
        }
        provider_settings = {
            provider: self.config["providers"][provider]["enabled"].get(bool)
            for provider in BUILTIN_PROVIDER_NAMES
        }
        try:
            resolution_config = self.config["resolution"]
            unknown_sections = set(resolution_config.keys()) - _RESOLUTION_SECTIONS
            if unknown_sections:
                unknown = sorted(unknown_sections)[0]
                raise ResolutionSettingsError(f"unknown resolution section {unknown!r}")
            return resolution_policy_from_settings(
                field_settings,
                provider_settings,
                authority_settings=resolution_config["authority"].get(dict),
                min_confidence_settings=resolution_config["min_confidence"].get(dict),
                preserve_existing_settings=resolution_config["preserve_existing"].get(dict),
            )
        except (confuse.ConfigError, ResolutionSettingsError) as error:
            raise ui.UserError(
                f"noqlenmeta: invalid resolution configuration: {error}"
            ) from None

    @staticmethod
    def _has_contributing_release_provider(policy: ResolutionPolicy) -> bool:
        return any(
            provider_can_contribute(policy, spec)
            for spec in BUILTIN_RELEASE_PROVIDER_SPECS.values()
        )

    @staticmethod
    def _has_contributing_track_provider(policy: ResolutionPolicy) -> bool:
        return any(
            provider_can_contribute(policy, spec)
            for spec in BUILTIN_TRACK_PROVIDER_SPECS.values()
        )

    def _build_import_track_plan(
        self,
        selected: SelectedImportTrack,
        context: TrackEnrichmentContext,
        *,
        from_scratch: bool,
        policy: ResolutionPolicy,
    ) -> ImportTrackPlanningResult:
        candidates: list[MetadataCandidate] = []
        if provider_can_contribute(policy, LRCLIB_SPEC):
            candidates.extend(
                self._collect_provider_candidates(
                    LRCLIB_SPEC,
                    lambda: self._lrclib_candidates(context),
                )
            )
        return build_import_track_planning_result(
            selected,
            context,
            from_scratch=from_scratch,
            candidates=candidates,
            policy=policy,
        )

    def _build_change_plan_for_release(
        self,
        context: ReleaseEnrichmentContext,
        current_values: Mapping[str, MetadataValue],
        policy: ResolutionPolicy,
    ) -> ChangePlan:
        candidates: list[MetadataCandidate] = []
        if provider_can_contribute(policy, DISCOGS_SPEC):
            token = resolve_discogs_token(
                self.config["providers"]["discogs"]["user_token"].as_str()
            )
            candidates.extend(
                self._collect_provider_candidates(
                    DISCOGS_SPEC,
                    lambda: self._discogs_candidates(context, token),
                )
            )

        if provider_can_contribute(policy, MUSICBRAINZ_SPEC):
            candidates.extend(
                self._collect_provider_candidates(
                    MUSICBRAINZ_SPEC,
                    lambda: self._musicbrainz_candidates(context),
                )
            )

        if provider_can_contribute(policy, LASTFM_SPEC):
            candidates.extend(
                self._collect_provider_candidates(
                    LASTFM_SPEC,
                    lambda: self._lastfm_candidates(context),
                )
            )

        if provider_can_contribute(policy, ITUNES_SPEC):
            storefront = self.config["providers"]["itunes"]["storefront"].as_str()
            candidates.extend(
                self._collect_provider_candidates(
                    ITUNES_SPEC,
                    lambda: self._itunes_candidates(context, storefront),
                )
            )

        return build_change_plan(resolve_metadata(current_values, candidates, policy))

    def _collect_provider_candidates(
        self,
        spec: ProviderSpec,
        fetch: Callable[[], Sequence[MetadataCandidate]],
    ) -> tuple[MetadataCandidate, ...]:
        try:
            candidates = fetch()
        except ProviderError:
            self._log.warning(
                "Noqlen Meta: {} enrichment unavailable; processing will continue",
                spec.display_name,
            )
            return ()

        validated = validate_provider_candidates(spec, candidates)
        self._log.debug(
            "{} enrichment returned {} candidate fields",
            spec.display_name,
            len(validated),
        )
        return validated

    def _discogs_candidates(
        self, context: ReleaseEnrichmentContext, token: str | None
    ) -> tuple[MetadataCandidate, ...]:
        try:
            from beetsplug.noqlenmeta.providers.discogs import DiscogsProvider
        except ModuleNotFoundError as error:
            if error.name == "discogs_client" or (
                error.name and error.name.startswith("discogs_client.")
            ):
                raise ProviderError("Discogs client dependency is unavailable") from None
            raise

        return tuple(DiscogsProvider(token=token).get_candidates(context))

    def _musicbrainz_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.musicbrainz import MusicBrainzProvider

        return tuple(MusicBrainzProvider().get_candidates(context))

    def _itunes_candidates(
        self, context: ReleaseEnrichmentContext, storefront: str
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

        return tuple(ITunesProvider(storefront=storefront).get_candidates(context))

    def _lastfm_candidates(
        self, context: ReleaseEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.lastfm import LastFmProvider

        if self._lastfm_provider is None:
            self._lastfm_provider = LastFmProvider()
        return tuple(self._lastfm_provider.get_candidates(context))

    def _lrclib_candidates(
        self, context: TrackEnrichmentContext
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.lrclib import LRCLIBProvider

        if self._lrclib_provider is None:
            self._lrclib_provider = LRCLIBProvider()
        return tuple(self._lrclib_provider.get_candidates(context))
