import unittest
from util.types import Artist, AlbumResults, SingleResults
from process.artist import get_topic_channel_id


def get_artist(name: str, channel_id: str, topic_channel: str) -> Artist:
    album_results: AlbumResults = {
        "browseId": None,
        "results": [],
        "params": None,
    }
    single_results: SingleResults = {
        "browseId": None,
        "results": [],
        "params": None,
    }
    return {
        "topic_channel_id": topic_channel,
        "description": "...",
        "views": "...",
        "name": name,
        "channelId": channel_id,
        "thumbnails": [],
        "albums": album_results,
        "singles": single_results,
    }


# name, channel_id, topic_channel_id
ARTISTS: list[tuple[str, str, str]] = [
    ("Maroon 5", "UCN1hnUccO4FD5WfM7ithXaw", "UCdFe4KkWwZ_twpo-UECR-Nw"),
    ("Depeche Mode", "UCM-CWGUijAC-8idv6k6Fygw", "UC-CcyIM_seGnGL5-2Fsppow"),
    ("Diabula Rasa", "UCdWkOp35b1rIDgkgmPXoEfQ", "UCdWkOp35b1rIDgkgmPXoEfQ")
]


class TestTopicChannelSearch(unittest.TestCase):
    def test(self) -> None:
        for artist_data in ARTISTS:
            artist: Artist = get_artist(*artist_data)
            found_topic_channel: str = get_topic_channel_id(artist)
            self.assertEqual(
                artist["topic_channel_id"],
                found_topic_channel,
                f'Expected topic channel id "{artist["topic_channel_id"]}", found id "{found_topic_channel}" for artist {artist["name"]}.',
            )
