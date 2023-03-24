import unittest
from util.types import Artist
from process.artist import get_topic_channel_id


ARTISTS: list[Artist] = [{
    'topic_channel_id': 'UCdFe4KkWwZ_twpo-UECR-Nw',
    'description': '...',
    'views': '...',
    'name': 'Maroon 5',
    'channelId': 'UCN1hnUccO4FD5WfM7ithXaw',
    'thumbnails': [],
    'albums': [],
    'singles': [],
}]



class TestTopicChannelSearch(unittest.TestCase):
    def test(self) -> None:
        for artist in ARTISTS:
            found_topic_channel: str = get_topic_channel_id(artist)
            self.assertEqual(artist['topic_channel_id'], found_topic_channel, f'Expected topic channel id "{artist["topic_channel_id"]}", found id "{found_topic_channel}" for artist {artist["name"]}.')
