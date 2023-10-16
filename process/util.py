from __future__ import annotations
from typing import List, Optional, Tuple, Dict

from youtubesearchpython import VideosSearch
from ytmusicapi import YTMusic
from pytube import Playlist
from fuzzywuzzy import fuzz, process
from util.types import YoutubeSearchVideoResult, Album, Track

ytmusic: YTMusic = YTMusic()


def video_search(query: str) -> List[YoutubeSearchVideoResult]:
    search = VideosSearch(query)
    return search.result()["result"]


def get_best_match(present_titles: List[str], current_track: Track) -> int:
    result: Optional[Tuple[str, int]] = process.extractOne(current_track['title'], present_titles, scorer=fuzz.ratio)
    if result:
        return result[1]
    return 0


def match_playlist_and_album(album: Album) -> List[Optional[str]]:
    """
    Matches titles from an album to a playlist as best as possible
    :param album: the album containing the titles
    :return: a list containing an optional video url per track
    """
    playlist: Playlist = Playlist(f'https://www.youtube.com/playlist?list={album["audioPlaylistId"]}')
    # album_len will be decreased by one per removed track
    album_len: int = len(album['tracks'])
    playlist_len: int = len(playlist.video_urls)
    if playlist_len == album_len:
        return list(playlist.video_urls)
    if len(playlist.video_urls) > len(album['tracks']):
        raise RuntimeError('More videos present in playlist than in album')
    if playlist_len == 0:
        raise RuntimeError('Empty playlist')
    videos: List[str] = [video.title for video in playlist.videos]
    rating: Dict[int, int] = {
        i: get_best_match(videos, track)
        for i, track in enumerate(album['tracks'])
    }
    while album_len > playlist_len:
        worst_score: int = min(rating.values())
        worst_idx: Optional[int] = None
        for i, v in rating.items():
            if v == worst_score:
                worst_idx = i
                break
        assert worst_idx is not None
        del rating[worst_idx]
        album_len -= 1
    playlist_urls = (url for url in playlist.video_urls)
    return [
        next(playlist_urls) if idx in rating else None
        for idx in range(len(album['tracks']))
    ]
