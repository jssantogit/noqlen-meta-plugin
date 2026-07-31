"""Noqlen Meta beets plugin."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

import confuse
from beets import ui
from beets.autotag import AlbumMatch, TrackMatch
from beets.library import Album, Library
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand

from beetsplug.noqlenmeta.beets_application import (
    BeetsApplicationMode,
    apply_beets_target_plan,
    parse_application_mode,
)
from beetsplug.noqlenmeta.beets_mapping import map_change_plan_to_beets
from beetsplug.noqlenmeta.changeplan import ChangePlan, build_change_plan
from beetsplug.noqlenmeta.domain import (
    MetadataCandidate,
    MetadataValue,
    ReleaseEnrichmentContext,
    TrackEnrichmentContext,
)
from beetsplug.noqlenmeta.identity import (
    BeetsMusicBrainzIdentitySource,
    IdentityImportApplicationResult,
    IdentitySourceError,
    ImportIdentityAuditResult,
    MusicBrainzIdentitySource,
    apply_import_identity_plan,
    audit_with_musicbrainz_source,
    identity_context_from_selected_import,
    map_identity_audit_to_import_targets,
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
    audit_library_identity_target,
    exact_snapshot_from_library_target,
    identity_context_from_library_target,
    refresh_library_identity_target,
    select_library_identity_targets,
)
from beetsplug.noqlenmeta.identity.library_application import (
    LibraryIdentityApplicationError,
    LibraryIdentityApplicationResult,
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
    BUILTIN_PROVIDER_SPECS,
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

_FIELD_DEFAULTS = {
    "genres": True,
    "styles": True,
    "labels": True,
    "catalog_numbers": True,
    "barcodes": True,
    "country": True,
    "year": True,
    "media": True,
    "format_descriptions": True,
    "mood": False,
    "lyrics": False,
    "synced_lyrics": False,
    "cover": False,
}
_RESOLUTION_SECTIONS = frozenset({"authority", "min_confidence", "preserve_existing"})


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

    def __init__(self) -> None:
        super().__init__()
        self.config.add(
            {
                "preview": True,
                "apply": False,
                "apply_mode": "strict",
                "identity": {
                    "enabled": False,
                    "preview": True,
                    "apply": False,
                },
                "fields": _FIELD_DEFAULTS,
                "providers": {
                    "discogs": {
                        "enabled": False,
                        "user_token": "",
                    },
                    "musicbrainz": {
                        "enabled": False,
                    },
                    "lastfm": {
                        "enabled": False,
                    },
                    "itunes": {
                        "enabled": False,
                        "storefront": "us",
                    },
                    "lrclib": {
                        "enabled": False,
                    },
                },
                "resolution": {
                    "authority": {},
                    "min_confidence": {},
                    "preserve_existing": {},
                },
            }
        )
        self.config["providers"]["discogs"]["user_token"].redact = True
        self._lastfm_provider = None
        self._lrclib_provider = None
        self._musicbrainz_identity_source: MusicBrainzIdentitySource | None = None
        self.register_listener("import_task_choice", self._import_task_choice)
        self._command = Subcommand(
            "noqlenmeta",
            help="preview Noqlen metadata enrichment or MusicBrainz identity for the library",
            aliases=["nm"],
        )
        self._command.parser.add_option(
            "--identity",
            dest="identity",
            action="store_true",
            default=False,
            help="audit MusicBrainz identity instead of ordinary metadata enrichment",
        )
        self._command.parser.add_option(
            "--all",
            dest="all",
            action="store_true",
            default=False,
            help="explicitly process every album in the library",
        )
        self._command.parser.add_option(
            "--apply",
            dest="apply",
            action="store_true",
            default=False,
            help="strictly persist eligible metadata to the library database",
        )
        self._command.parser.add_option(
            "--partial",
            dest="partial",
            action="store_true",
            default=False,
            help="with --apply, persist mapped fields and withhold unresolved fields",
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
        if bool(getattr(opts, "identity", False)):
            self._command_library_identity(lib, opts, args)
            return
        all_albums = bool(getattr(opts, "all", False))
        apply_enabled = bool(getattr(opts, "apply", False))
        partial_enabled = bool(getattr(opts, "partial", False))
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

        for album_plan in prepared:
            application_result: LibraryApplicationResult | None = None
            if apply_enabled:
                application_result = apply_library_target_plan(
                    album_plan.album,
                    album_plan.target_plan,
                    mode=application_mode,
                )
            render_library_target_plan(
                album_plan.album,
                album_plan.target_plan,
                application_result,
                position=album_plan.position,
                total=album_plan.total,
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

        targets = select_library_identity_targets(lib, args if args else None)
        if not targets:
            ui.print_("Noqlen MusicBrainz identity: no Items matched")
            return

        context_results = tuple(identity_context_from_library_target(target) for target in targets)
        source = self._identity_source() if any(context_results) else None
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
                result = audit_library_identity_target(target, source)
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

        application_results: dict[int, LibraryIdentityApplicationResult] = {}
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
            for record in prepared:
                if record.target_plan is not None:
                    application_results[record.position] = apply_library_identity_plan(
                        lib, record.target_plan
                    )

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
                application_results.get(record.position),
                apply_requested=apply_enabled,
                position=record.position,
                total=record.total,
            )

    def _resolution_policy(self) -> ResolutionPolicy:
        field_settings = {
            field: self.config["fields"][field].get(bool) for field in _FIELD_DEFAULTS
        }
        provider_settings = {
            provider: self.config["providers"][provider]["enabled"].get(bool)
            for provider in BUILTIN_PROVIDER_SPECS
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
