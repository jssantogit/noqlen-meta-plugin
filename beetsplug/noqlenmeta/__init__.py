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
_ITUNES_FIELDS = ("genres", "year")


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
                for provider in ("discogs", "itunes")
            },
        )
        itunes_can_contribute = policy.provider_can_contribute("itunes") and any(
            policy.is_field_enabled(field)
            and policy.authority_rank(field, "itunes") is not None
            for field in _ITUNES_FIELDS
        )
        if not policy.provider_can_contribute("discogs") and not itunes_can_contribute:
            return

        context = context_from_album_info(album_info)
        if context is None:
            self._log.debug("Noqlen Meta preview skipped: selected release has no album identity")
            return

        current_values = current_values_from_album_info(album_info)
        candidates: list[MetadataCandidate] = []
        if policy.provider_can_contribute("discogs"):
            token = resolve_discogs_token(
                self.config["providers"]["discogs"]["user_token"].as_str()
            )
            try:
                discogs_candidates = self._discogs_candidates(context, token)
            except ProviderError:
                self._log.warning(
                    "Noqlen Meta: Discogs enrichment unavailable; import will continue"
                )
            else:
                self._log.debug(
                    "Discogs enrichment returned {} candidate fields", len(discogs_candidates)
                )
                candidates.extend(discogs_candidates)

        if itunes_can_contribute:
            storefront = self.config["providers"]["itunes"]["storefront"].as_str()
            try:
                itunes_candidates = self._itunes_candidates(context, storefront)
            except ProviderError:
                self._log.warning(
                    "Noqlen Meta: iTunes enrichment unavailable; import will continue"
                )
            else:
                self._log.debug(
                    "iTunes enrichment returned {} candidate fields", len(itunes_candidates)
                )
                candidates.extend(itunes_candidates)

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

    def _itunes_candidates(
        self, context: ReleaseEnrichmentContext, storefront: str
    ) -> tuple[MetadataCandidate, ...]:
        from beetsplug.noqlenmeta.providers.itunes import ITunesProvider

        return tuple(ITunesProvider(storefront=storefront).get_candidates(context))
