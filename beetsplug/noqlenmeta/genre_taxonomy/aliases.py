"""Small reviewed semantic additions to the MusicBrainz genre taxonomy."""

ALIASES = {
    "kpop": "K-pop",
    "k-pop": "K-pop",
    "rnb": "R&B",
    "r&b": "R&B",
    "dnb": "Drum and Bass",
    "drum n bass": "Drum and Bass",
    "drum & bass": "Drum and Bass",
}

BROAD_GENRES = frozenset(
    {
        "Blues",
        "Classical",
        "Country",
        "Electronic",
        "Folk",
        "Hip Hop",
        "Jazz",
        "Latin",
        "Metal",
        "Pop",
        "R&B",
        "Reggae",
        "Rock",
    }
)

MOODS = frozenset(
    {
        "Aggressive",
        "Atmospheric",
        "Chill",
        "Dark",
        "Dreamy",
        "Energetic",
        "Happy",
        "Melancholic",
        "Sad",
    }
)
ORIGINS = frozenset({"Korean"})
DESCRIPTORS = frozenset({"Girl Group"})
NOISE_LABELS = frozenset(
    {
        "album",
        "albums i own",
        "favorite",
        "favorites",
        "female vocalists",
        "last.fm",
        "personal",
        "seen live",
        "song",
        "spotify",
        "track",
        "vocal",
    }
)
