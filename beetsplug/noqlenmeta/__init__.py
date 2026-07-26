"""Noqlen Meta beets plugin."""

from collections.abc import Callable, Sequence

from beets.plugins import BeetsPlugin

from beetsplug.noqlenmeta.beets_application import apply_beets_target_plan
from beetsplug.noqlenmeta.beets_mapping import map_change_plan_to_beets
from beetsplug.noqlenmeta.changeplan import build_change_plan
from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    current_values_from_album_info,
    eligible_album_info,
    render_beets_target_plan,
    resolution_policy_from_settings,
    resolve_discogs_token,
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
from beetsplug.noqlenmeta.resolver import resolve_metadata

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
class NoqlenMetaPlugin(BeetsPlugin):
    """Entry point loaded by beets as the ``noqlenmeta`` plugin."""

    def __init__(self) -> None:
        super().__init__()
        self.config.add(
            {
                "preview": True,
                "apply": False,
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

    def _import_task_choice(self, session: object, task: object) -> None:
        album_info = eligible_album_info(task)
        if album_info is None:
            return

        policy = resolution_policy_from_settings(
            {field: self.config["fields"][field].get(bool) for field in _FIELD_DEFAULTS},
            {
                provider: self.config["providers"][provider]["enabled"].get(bool)
                for provider in BUILTIN_PROVIDER_SPECS
            },
        )
        if not any(
            provider_can_contribute(policy, spec)
            for spec in BUILTIN_PROVIDER_SPECS.values()
        ):
            return

        context = context_from_album_info(album_info)
        if context is None:
            self._log.debug("Noqlen Meta preview skipped: selected release has no album identity")
            return

        current_values = current_values_from_album_info(album_info)
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

        decisions = resolve_metadata(current_values, candidates, policy)
        change_plan = build_change_plan(decisions)
        target_plan = map_change_plan_to_beets(change_plan)
        application_result = None
        apply_enabled = self.config["apply"].get(bool)
        if apply_enabled:
            application_result = apply_beets_target_plan(album_info, target_plan)
        if self.config["preview"].get(bool):
            render_beets_target_plan(target_plan, application_result)
        elif apply_enabled and application_result is not None:
            if application_result.is_blocked:
                self._log.warning(
                    "Noqlen Meta: application blocked by unresolved review or target mapping"
                )
            elif application_result.has_applied_changes:
                self._log.info(
                    "Noqlen Meta: prepared {} selected-release metadata field(s) "
                    "for beets application",
                    len(application_result.applied_changes),
                )
            else:
                self._log.info(
                    "Noqlen Meta: no selected-release metadata changes prepared "
                    "for beets application"
                )

    def _collect_provider_candidates(
        self,
        spec: ProviderSpec,
        fetch: Callable[[], Sequence[MetadataCandidate]],
    ) -> tuple[MetadataCandidate, ...]:
        try:
            candidates = fetch()
        except ProviderError:
            self._log.warning(
                "Noqlen Meta: {} enrichment unavailable; import will continue",
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
