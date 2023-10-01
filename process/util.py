from __future__ import annotations
from typing import List

from youtubesearchpython import VideosSearch
from ytmusicapi import YTMusic
from util.types import YoutubeSearchVideoResult

ytmusic: YTMusic = YTMusic()


def video_search(query: str) -> List[YoutubeSearchVideoResult]:
    search = VideosSearch(query)
    return search.result()["result"]
