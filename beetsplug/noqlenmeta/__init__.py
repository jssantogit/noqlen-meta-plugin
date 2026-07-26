"""Noqlen Meta beets plugin."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from beets import ui
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
)
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    current_values_from_album_info,
    eligible_album_info,
    render_beets_target_plan,
    resolution_policy_from_settings,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.library_application import (
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
    DISCOGS_SPEC,
    ITUNES_SPEC,
    ProviderSpec,
)
from beetsplug.noqlenmeta.resolver import ResolutionPolicy, resolve_metadata

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


@dataclass(frozen=True, slots=True)
class LibraryAlbumPlan:
    """One prepared command plan retained until every Album is planned."""

    album: Album
    target_plan: LibraryTargetPlan
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
                "fields": _FIELD_DEFAULTS,
                "providers": {
                    "discogs": {
                        "enabled": False,
                        "user_token": "",
                    },
                    "itunes": {
                        "enabled": False,
                        "storefront": "us",
                    },
                },
            }
        )
        self.config["providers"]["discogs"]["user_token"].redact = True
        self.register_listener("import_task_choice", self._import_task_choice)
        self._command = Subcommand(
            "noqlenmeta",
            help="preview Noqlen metadata enrichment for library albums",
            aliases=["nm"],
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
        self._command.func = self._command_noqlenmeta

    def commands(self) -> list[Subcommand]:
        return [self._command]

    def _import_task_choice(self, session: object, task: object) -> None:
        album_info = eligible_album_info(task)
        if album_info is None:
            return

        apply_enabled = self.config["apply"].get(bool)
        application_mode = BeetsApplicationMode.STRICT
        if apply_enabled:
            application_mode = parse_application_mode(self.config["apply_mode"].as_str())

        policy = self._resolution_policy()
        if not self._has_contributing_provider(policy):
            return

        context = context_from_album_info(album_info)
        if context is None:
            self._log.debug("Noqlen Meta preview skipped: selected release has no album identity")
            return

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
        if self.config["preview"].get(bool):
            render_beets_target_plan(target_plan, application_result)
        elif apply_enabled and application_result is not None:
            if application_result.is_blocked:
                self._log.warning(
                    "Noqlen Meta: application blocked by unresolved review or target mapping"
                )
            elif application_result.has_applied_changes:
                if application_result.has_withheld_fields:
                    self._log.info(
                        "Noqlen Meta: prepared {} selected-release metadata field(s) for "
                        "beets application; {} review and {} mapping blocker withheld",
                        len(application_result.applied_changes),
                        application_result.resolution_review_count,
                        application_result.mapping_blocker_count,
                    )
                else:
                    self._log.info(
                        "Noqlen Meta: prepared {} selected-release metadata field(s) "
                        "for beets application",
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

    def _command_noqlenmeta(self, lib: Library, opts: object, args: list[str]) -> None:
        all_albums = bool(getattr(opts, "all", False))
        apply_enabled = bool(getattr(opts, "apply", False))
        has_query = any(isinstance(argument, str) and argument.strip() for argument in args)
        if not has_query and not all_albums:
            raise ui.UserError("noqlenmeta: provide an album query or use --all")
        if args and all_albums:
            raise ui.UserError("noqlenmeta: use an album query or --all, not both")

        policy = self._resolution_policy()
        if not self._has_contributing_provider(policy):
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
                )
            render_library_target_plan(
                album_plan.album,
                album_plan.target_plan,
                application_result,
                position=album_plan.position,
                total=album_plan.total,
            )

    def _resolution_policy(self) -> ResolutionPolicy:
        return resolution_policy_from_settings(
            {field: self.config["fields"][field].get(bool) for field in _FIELD_DEFAULTS},
            {
                provider: self.config["providers"][provider]["enabled"].get(bool)
                for provider in BUILTIN_PROVIDER_SPECS
            },
        )

    @staticmethod
    def _has_contributing_provider(policy: ResolutionPolicy) -> bool:
        return any(
            provider_can_contribute(policy, spec)
            for spec in BUILTIN_PROVIDER_SPECS.values()
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

    def _itunes_candidates(
        self, context: ReleaseEnrichmentContext, storefront: str
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

        return tuple(ITunesProvider(storefront=storefront).get_candidates(context))
