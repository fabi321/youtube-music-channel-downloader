import unittest
from process.util import match_playlist_and_album
from util.types import Track, Album, Artist, AlbumResults, SingleResults


def get_album(
    tracks: tuple[str],
    album_title: str,
    playlist_id: str,
    *_: str,
) -> Album:
    conv_tracks: list[Track] = [
        {
            "videoId": "...",
            "title": track,
            "artists": [],
            "album": "...",
            "duration": "...",
            "duration_seconds": 0,
            "thumbnails": None,
            "isAvailable": True,
            "isExplicit": False,
        }
        for track in tracks
    ]
    album: Album = {
        "title": album_title,
        "thumbnails": [],
        "artists": [],
        "year": "...",
        "trackCount": 0,
        "duration": "...",
        "duration_seconds": 0,
        "tracks": conv_tracks,
        "audioPlaylistId": playlist_id,
        "browseId": "...",
        "path": "...",
    }
    return album


# track_titles, album_title, album_playlist_id, expected_video_ids
VIDEOS: list[tuple[tuple[str, ...], str, str, tuple[str, ...]]] = [
    (
        (
            "My Cosmos Is Mine",
            "Wagging Tongue",
            "Ghosts Again",
            "Don't Say You Love Me",
            "My Favourite Stranger",
            "Soul With Me",
            "Caroline's Monkey",
            "Before We Drown",
            "People Are Good",
            "Always You",
            "Never Let Me Go",
            "Speak To Me",
        ),
        "Memento Mori",
        "OLAK5uy_kBh1orlQqYtUQg2DxVgQjE8hXv91Ra14s",
        (
            "https://www.youtube.com/watch?v=LbDb4Qc_NCU",
            "https://www.youtube.com/watch?v=2tQ0FDUYARM",
            "https://www.youtube.com/watch?v=lpHKtk-WC0Q",
            "https://www.youtube.com/watch?v=nw12TV4NM6k",
            "https://www.youtube.com/watch?v=Hjj2n7_ndeE",
            "https://www.youtube.com/watch?v=GkVyVrzBFNQ",
            "https://www.youtube.com/watch?v=AucplQIb2as",
            "https://www.youtube.com/watch?v=M4XXiAoAAfw",
            "https://www.youtube.com/watch?v=AFfS7PZD6YE",
            "https://www.youtube.com/watch?v=0Y9W0IhHMag",
            "https://www.youtube.com/watch?v=KkbCpI2eM8A",
            "https://www.youtube.com/watch?v=almCjaTa0Ts",
        ),
    ),
    (
        (
            "Given Up",
            "Valentine's Day (Live at Festhalle, Frankfurt, DE, 1/20/2008)",
            "In Between (Live at the O2 Arena, London, England, 1/29/2008)",
        ),
        "Given Up",
        "OLAK5uy_mj9q02ANDBRiZY3Mc2OMDSUhuqRgPlx_U",
        (
            "https://www.youtube.com/watch?v=_u5kGSn0cSM",
            None,
            None,
        ),
    ),
    (
        (
            "Magic",
            "Suddenly",
            "Dancin'",
            "Suspended In Time",
            "Whenever You're Away from Me",
            "I'm Alive",
            "The Fall",
            "Don't Walk Away",
            "All Over the World",
            "Xanadu",
        ),
        "Xanadu - Original Motion Picture Soundtrack",
        "OLAK5uy_kniZCx-4GnXA0euH2mflVFTMl5v68bR04",
        (
            None,
            None,
            None,
            None,
            None,
            "https://www.youtube.com/watch?v=7tPF-kUJIIo",
            "https://www.youtube.com/watch?v=QcqvUAlhH0E",
            "https://www.youtube.com/watch?v=h7ekIoRrtBs",
            "https://www.youtube.com/watch?v=7iFE-Mb2JiI",
            "https://www.youtube.com/watch?v=mX8Y_LUxIJo",
        ),
    ),
]


class TestVideoSearch(unittest.TestCase):
    def test(self) -> None:
        for video_data in VIDEOS:
            print(f"Testing {video_data}")
            album = get_album(*video_data)
            video_ids = match_playlist_and_album(album)
            self.assertEqual(video_ids, list(video_data[3]), "Invalid video found")
