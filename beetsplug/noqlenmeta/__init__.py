"""Noqlen Meta beets plugin."""

from beets.plugins import BeetsPlugin

from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    current_values_from_album_info,
    eligible_album_info,
    render_resolved_preview,
    resolution_policy_from_settings,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.providers import ProviderError
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
                "fields": _FIELD_DEFAULTS,
                "providers": {
                    "discogs": {
                        "enabled": False,
                        "user_token": "",
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
            {"discogs": self.config["providers"]["discogs"]["enabled"].get(bool)},
        )
        if not policy.provider_can_contribute("discogs"):
            return

        context = context_from_album_info(album_info)
        if context is None:
            self._log.debug("Discogs preview skipped: selected release has no album identity")
            return

        current_values = current_values_from_album_info(album_info)
        token = resolve_discogs_token(
            self.config["providers"]["discogs"]["user_token"].as_str()
        )
        try:
            candidates = self._discogs_candidates(context, token)
        except ProviderError:
            self._log.warning("Noqlen Meta: Discogs enrichment unavailable; import will continue")
            return

        self._log.debug("Discogs enrichment returned {} candidate fields", len(candidates))
        decisions = resolve_metadata(current_values, candidates, policy)
        if decisions and self.config["preview"].get(bool):
            render_resolved_preview(decisions)

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
