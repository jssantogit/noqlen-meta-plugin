"""Explicitly refresh the packaged genre snapshot from MusicBrainz."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://musicbrainz.org/ws/2/genre/all?fmt=txt"
USER_AGENT = "NoqlenMeta/1.0.0 (https://github.com/jssantogit/noqlen-meta-plugin)"
TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 2_000_000
TARGET = Path(__file__).parents[1] / "beetsplug/noqlenmeta/genre_taxonomy/genres.txt"
_WHITESPACE = re.compile(r"\s+")
_TOKEN_CASING = {
    "aor": "AOR",
    "asmr": "ASMR",
    "eai": "EAI",
    "ebm": "EBM",
    "edm": "EDM",
    "idm": "IDM",
    "nrg": "NRG",
    "nwobhm": "NWOBHM",
    "r&b": "R&B",
    "uk": "UK",
    "uk82": "UK82",
    "us": "US",
}
_LOWERCASE_WORDS = frozenset({"and", "of", "the"})


def _display_token(token: str) -> str:
    folded = token.casefold()
    if folded in _TOKEN_CASING:
        return _TOKEN_CASING[folded]

    segments = token.split("-")
    if len(segments) == 2 and len(segments[0]) == 1 and segments[1].casefold() == "pop":
        return f"{segments[0].upper()}-pop"
    return "-".join(
        _TOKEN_CASING.get(segment.casefold(), segment.title()) for segment in segments
    )


def _canonical_name(value: str) -> str:
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value).strip())
    words = normalized.split(" ") if normalized else []
    return " ".join(
        word.casefold()
        if index and word.casefold() in _LOWERCASE_WORDS
        else _display_token(word)
        for index, word in enumerate(words)
    )


def _normalized_snapshot(body: bytes) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("MusicBrainz genre response is not valid UTF-8") from None
    names = [_canonical_name(line) for line in text.splitlines()]
    names = [name for name in names if name]
    if not names:
        raise ValueError("MusicBrainz genre response is empty")
    identities = [name.casefold() for name in names]
    if len(identities) != len(set(identities)):
        raise ValueError("MusicBrainz genre response contains duplicate identities")
    names.sort(key=lambda name: (name.casefold(), name))
    return ("\n".join(names) + "\n").encode("utf-8")


def main() -> None:
    request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("MusicBrainz genre response exceeded the size limit")
    snapshot = _normalized_snapshot(body)
    old = TARGET.read_bytes() if TARGET.exists() else b""
    TARGET.write_bytes(snapshot)
    print(f"genres: {len(old.splitlines())} -> {len(snapshot.splitlines())}")
    print(f"sha256: {hashlib.sha256(snapshot).hexdigest()}")


if __name__ == "__main__":
    main()
