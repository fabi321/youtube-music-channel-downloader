import unittest
from process.track import get_alternative_track_id
from util.types import Track, Album, Artist, AlbumResults, SingleResults


def get_track_album_artist(
    track_title: str,
    track_length: str,
    album_title: str,
    artist_name: str,
    *_: str,
) -> tuple[Track, Album, Artist]:
    track: Track = {
        'videoId': '...',
        'title': track_title,
        'artists': [],
        'album': '...',
        'duration': track_length,
        'duration_seconds': 0,
        'thumbnails': None,
        'isAvailable': True,
        'isExplicit': False,
    }
    album: Album = {
        'title': album_title,
        'thumbnails': [],
        'artists': [],
        'year': '...',
        'trackCount': 0,
        'duration': '...',
        'duration_seconds': 0,
        'tracks': [track],
        'audioPlaylistId': '...',
    }
    album_results: AlbumResults = {
        'browseId': None,
        'results': [],
        'params': None,
    }
    single_results: SingleResults = {
        'browseId': None,
        'results': [],
        'params': None,
    }
    artist: Artist = {
        'topic_channel_id': '...',
        'description': '...',
        'views': '...',
        'name': artist_name,
        'channelId': '...',
        'thumbnails': [],
        'albums': album_results,
        'singles': single_results,
    }
    return track, album, artist


# track_title, album_title, artist_name, artist_topic_channel, expected_video_id
VIDEOS: list[tuple[str, str, str, str, str]] = [
    ("Enjoy the Silence", '6:12', "Violator", "Depeche Mode", "Vd_nkokQwnQ"),
    ("CHOKE", '3:52', "ERROR", "The Warning", "1oH3ytQFj3g"),  # album track
    ("CHOKE", '2:41', "CHOKE", "The Warning", "mImB6l5nepA"),  # 2022 single
    # The following is basically impossible to find, as it has the same duration as the album version
    ("CHOKE", '3:52', "CHOKE", "The Warning", "k6guyvnpKjU"),  # 2021 single
    # Title is without brackets
    ("John the Revelator (Single Version)", '3:17', "Playing The Angel (The 12\" Singles)", "Depeche Mode", "A-pB7idn5d4"),
    # Album is without brackets
    ("Cover Me", '4:52', "Spirit (Deluxe)", "Depeche Mode", "1ptP7O1aCh8"),
]


class TestVideoSearch(unittest.TestCase):
    def test(self) -> None:
        for video_data in VIDEOS:
            print(f"Testing {video_data}")
            track, album, artist = get_track_album_artist(*video_data)
            video_id = get_alternative_track_id(track, album, artist)
            self.assertEqual(video_id, video_data[4], "Invalid video found")
