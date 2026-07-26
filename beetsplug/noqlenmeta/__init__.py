"""Noqlen Meta beets plugin."""

from beets.plugins import BeetsPlugin

from beetsplug.noqlenmeta.domain import MetadataCandidate, ReleaseEnrichmentContext
from beetsplug.noqlenmeta.integration import (
    context_from_album_info,
    eligible_album_info,
    render_preview,
    resolve_discogs_token,
)
from beetsplug.noqlenmeta.providers import ProviderError


class NoqlenMetaPlugin(BeetsPlugin):
    """Entry point loaded by beets as the ``noqlenmeta`` plugin."""

    def __init__(self) -> None:
        super().__init__()
        self.config.add(
            {
                "discogs": {
                    "enabled": False,
                    "user_token": "",
                },
                "preview": True,
            }
        )
        self.config["discogs"]["user_token"].redact = True
        self.register_listener("import_task_choice", self._import_task_choice)

    def _import_task_choice(self, session: object, task: object) -> None:
        if not self.config["discogs"]["enabled"].get(bool):
            return

        album_info = eligible_album_info(task)
        if album_info is None:
            return

        context = context_from_album_info(album_info)
        if context is None:
            self._log.debug("Discogs preview skipped: selected release has no album identity")
            return

        token = resolve_discogs_token(self.config["discogs"]["user_token"].as_str())
        try:
            candidates = self._discogs_candidates(context, token)
        except ProviderError:
            self._log.warning("Noqlen Meta: Discogs enrichment unavailable; import will continue")
            return

        self._log.debug("Discogs enrichment returned {} candidate fields", len(candidates))
        if candidates and self.config["preview"].get(bool):
            render_preview(candidates)

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
